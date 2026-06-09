"""
Last.fm Multi-Worker Scraper
-----------------------------
Runs N workers in parallel threads, all writing to one shared parquet.

Usage:
    python scraper.py                          # 6 workers, full dataset
    python scraper.py --workers 4              # 4 workers
    python scraper.py --start 300000 --end 600000          # specific range
    python scraper.py --workers 3 --start 0 --end 200000   # 3 workers, limited range
"""

import os, re, time, threading, argparse
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from filelock import FileLock

# ── Config ────────────────────────────────────────────────────────────────────
PARQUET_PATH = 'data/mb_album_artists.parquet'
OUT_PATH     = 'data/lastfm_data.parquet'
LOCK_PATH    = 'data/lastfm_data.parquet.lock'
SAVE_EVERY   = 30       # each worker flushes every N rows
SLEEP_ARTIST = 2.0      # seconds between retries
SLEEP_ALBUM  = 2.0
SLEEP_NEXT   = 1.5      # between albums

COLS = ['Artist', 'Album',
        'Artist_Listeners', 'Artist_Scrobbles',
        'Album_Listeners',  'Album_Scrobbles',
        'Similar_Artists',  'Artist_URL', 'Album_URL']

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36'
}

lock      = FileLock(LOCK_PATH, timeout=60)
print_lock = threading.Lock()   # so terminal lines don't mix

# ── Shared progress counters ──────────────────────────────────────────────────
_total_saved    = 0
_total_skipped  = 0
_counter_lock   = threading.Lock()

def log(worker_id, msg):
    with print_lock:
        print(f'[W{worker_id}] {msg}', flush=True)

# ── Scrapers ──────────────────────────────────────────────────────────────────
def scrape_artist(url):
    listeners, scrobbles, similar = 'N/A', 'N/A', 'None Found'
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                container = soup.find('div', class_='header-new-info-desktop')
                if container:
                    for item in container.find_all('li', class_='header-metadata-tnew-item'):
                        title = item.find('h4', class_='header-metadata-tnew-title')
                        abbr  = item.find('abbr', class_='js-abbreviated-counter')
                        if title and abbr:
                            if 'Listeners'  in title.text: listeners = abbr.get('title')
                            elif 'Scrobbles' in title.text: scrobbles = abbr.get('title')
                sims = [a.text.strip()
                        for h in soup.find_all('h3', class_='catalogue-overview-similar-artists-item-name')
                        for a in [h.find('a')] if a]
                if sims: similar = ', '.join(sims)
                if listeners != 'N/A': break
            time.sleep(SLEEP_ARTIST)
        except Exception as e:
            time.sleep(SLEEP_ARTIST)
    return listeners, scrobbles, similar

def scrape_album(url):
    listeners, scrobbles = 'N/A', 'N/A'
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                soup  = BeautifulSoup(r.text, 'html.parser')
                abbrs = soup.find_all('abbr', class_='js-abbreviated-counter')
                if len(abbrs) >= 2:
                    listeners = abbrs[0].get('title', 'N/A')
                    scrobbles = abbrs[1].get('title', 'N/A')
                elif len(abbrs) == 1:
                    listeners = abbrs[0].get('title', 'N/A')
                if listeners != 'N/A' and scrobbles != 'N/A': break
            time.sleep(SLEEP_ALBUM)
        except Exception as e:
            time.sleep(SLEEP_ALBUM)
    return listeners, scrobbles

# ── Parquet helpers ───────────────────────────────────────────────────────────
def load_done_set():
    if not os.path.exists(OUT_PATH):
        return set()
    df = pd.read_parquet(OUT_PATH, columns=['Artist', 'Album'])
    return set(zip(df['Artist'].str.lower(), df['Album'].str.lower()))

def flush_buffer(buffer):
    global _total_saved
    df_new = pd.DataFrame(buffer, columns=COLS)
    with lock:
        if os.path.exists(OUT_PATH):
            df_out = pd.concat([pd.read_parquet(OUT_PATH), df_new], ignore_index=True)
        else:
            df_out = df_new
        df_out = df_out.drop_duplicates(subset=['Artist', 'Album']).reset_index(drop=True)
        df_out.to_parquet(OUT_PATH, index=False)
        n = len(df_out)
    with _counter_lock:
        _total_saved = n
    return n

# ── Worker thread ─────────────────────────────────────────────────────────────
def worker(worker_id, df_slice, done_set, done_set_lock):
    global _total_skipped

    buffer   = []
    scraped  = 0
    skipped  = 0
    total    = len(df_slice)

    artist_col = 'artist_name' if 'artist_name' in df_slice.columns else 'name'
    album_col  = 'album_name'  if 'album_name'  in df_slice.columns else 'album'

    for i, row in df_slice.iterrows():
        artist = str(row[artist_col]).strip()
        album  = str(row[album_col]).strip()

        if not artist or artist.lower() in ('none', 'nan'):
            continue

        # ── Check before scraping ────────────────────────────────────────────
        key = (artist.lower(), album.lower())
        with done_set_lock:
            if key in done_set:
                skipped += 1
                with _counter_lock:
                    _total_skipped += 1
                log(worker_id, f'SKIP [{i+1}/{total}] {artist} — {album}')
                continue

        # ── Scrape ───────────────────────────────────────────────────────────
        a_slug     = artist.replace(' ', '+')
        al_slug    = album.replace(' ', '+')
        artist_url = f'https://www.last.fm/music/{a_slug}'
        album_url  = f'https://www.last.fm/music/{a_slug}/{al_slug}'

        log(worker_id, f'[{i+1}/{total}] {artist} — {album}')

        a_listeners, a_scrobbles, similar = scrape_artist(artist_url)
        time.sleep(1)
        al_listeners, al_scrobbles = scrape_album(album_url)

        buffer.append([artist, album,
                       a_listeners, a_scrobbles,
                       al_listeners, al_scrobbles,
                       similar, artist_url, album_url])

        with done_set_lock:
            done_set.add(key)
        scraped += 1

        # ── Flush every SAVE_EVERY rows ──────────────────────────────────────
        if len(buffer) >= SAVE_EVERY:
            total_saved = flush_buffer(buffer)
            buffer = []
            log(worker_id, f'-- saved -- total in parquet: {total_saved:,}')

        time.sleep(SLEEP_NEXT)

    # ── Final flush ──────────────────────────────────────────────────────────
    if buffer:
        total_saved = flush_buffer(buffer)
        buffer = []
        log(worker_id, f'-- final flush -- total in parquet: {total_saved:,}')

    log(worker_id, f'DONE — scraped: {scraped:,}  skipped: {skipped:,}')

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Last.fm multi-worker scraper')
    parser.add_argument('--workers', type=int, default=6,    help='Number of parallel workers (default: 6)')
    parser.add_argument('--start',   type=int, default=None, help='Start row (default: 0)')
    parser.add_argument('--end',     type=int, default=None, help='End row   (default: end of dataset)')
    args = parser.parse_args()

    # ── Load source data ─────────────────────────────────────────────────────
    print(f'Loading {PARQUET_PATH}...', flush=True)
    df_all = pd.read_parquet(PARQUET_PATH)
    artist_col = 'artist_name' if 'artist_name' in df_all.columns else 'name'
    album_col  = 'album_name'  if 'album_name'  in df_all.columns else 'album'

    df_unique = (
        df_all[[artist_col, album_col]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    total = len(df_unique)

    start = args.start if args.start is not None else 0
    end   = args.end   if args.end   is not None else total
    start = max(0, min(start, total))
    end   = max(0, min(end,   total))

    df_range = df_unique.iloc[start:end].reset_index(drop=True)

    print(f'Total unique albums  : {total:,}')
    print(f'Range to scrape      : rows {start:,} to {end:,}  ({len(df_range):,} albums)')
    print(f'Workers              : {args.workers}')
    print(f'Output               : {OUT_PATH}')
    print('-' * 60, flush=True)

    # ── Load done-set (shared across all workers) ────────────────────────────
    print('Loading already-scraped albums...', flush=True)
    done_set      = load_done_set()
    done_set_lock = threading.Lock()
    print(f'Already scraped: {len(done_set):,}', flush=True)
    print('-' * 60, flush=True)

    # ── Split range across workers ───────────────────────────────────────────
    chunk      = (len(df_range) + args.workers - 1) // args.workers
    threads    = []

    for wid in range(args.workers):
        s       = wid * chunk
        e       = min(s + chunk, len(df_range))
        if s >= len(df_range):
            break
        df_slice = df_range.iloc[s:e].reset_index(drop=True)
        t = threading.Thread(
            target=worker,
            args=(wid, df_slice, done_set, done_set_lock),
            daemon=True
        )
        threads.append(t)
        print(f'  Worker {wid}: rows {start+s:,} to {start+e:,}  ({len(df_slice):,} albums)', flush=True)

    print('-' * 60, flush=True)
    print('Starting all workers...\n', flush=True)

    start_time = time.time()
    for t in threads:
        t.start()

    # ── Wait for all workers to finish ───────────────────────────────────────
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print('\nStopped by user — progress is saved in parquet.', flush=True)

    elapsed = time.time() - start_time
    print('\n' + '=' * 60, flush=True)
    print(f'All workers finished in {elapsed/60:.1f} minutes', flush=True)
    print(f'Total saved in parquet : {_total_saved:,}', flush=True)
    print(f'Total skipped          : {_total_skipped:,}', flush=True)

if __name__ == '__main__':
    main()
