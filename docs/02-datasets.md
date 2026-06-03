# Datasets — Building DataFrames

**Notebook:** `1-EDA/02-parquet-to-dataframes.ipynb`

Loads the raw Parquet files into pandas DataFrames, enriches them, and persists the results as pickles for use in later stages.

## Output files

| File | Description |
|------|-------------|
| `data/pickles/final_album_df.pkl` | One row per album with all scalar features and tag dicts |
| `data/pickles/final_artist_df.pkl` | One row per artist with scalar features and tag dict |
| `data/pickles/master_df.pkl` | Albums joined with their primary artist's features |

## Processing steps

### 1. Load raw Parquet tables

```python
artists      = pd.read_parquet('data/mb_artist.parquet')
artist_tags  = pd.read_parquet('data/mb_artist_tag.parquet')
# ... all 10 tables
```

### 2. Aggregate tags into dicts

Tags are stored as one row per (album/artist, tag). They are grouped into `{tag_id: tag_count}` dicts per entity:

```python
album_tag_dict   = album_tags.groupby('album_id').apply(lambda x: dict(...))
artist_tag_dict  = ...  # artist tags mapped onto albums via artist_credit
label_tag_dict   = ...  # label tags mapped onto albums via album_label
```

### 3. Build `final_album_df`

Left-joins albums with ratings, country, label, and all three tag dicts:

```mermaid
flowchart LR
    A[mb_album] -->|left join| B[album_ratings]
    B -->|left join| C[album_country]
    C -->|left join| D[album_label]
    D -->|left join| E[album_tag_dict]
    E -->|left join| F[label_tag_dict]
    F --> G[final_album_df]
```

**Columns:** `album_id`, `album_name`, `artist_credit`, `rating`, `rating_count`, `language`, `country`, `album_year`, `label_id`, `label_type`, `album_tags`, `label_tags`

### 4. Build `final_artist_df`

Left-joins artists with ratings and aggregated artist tag dict.

**Columns:** `id`, `name`, `artist_year`, `type`, `area`, `gender`, `rating`, `rating_count`, `artist_tags`

### 5. Build `master_df`

Joins `final_album_df` with `final_artist_df` on `artist_credit → id`, bringing the artist's year, type, area, gender, rating, and tags onto each album row.

```mermaid
flowchart LR
    A[final_album_df] -->|left join on artist_credit = id| B[final_artist_df]
    B --> C[master_df]
```

`master_df` is the fully-denormalised view used for EDA and feature weight exploration.

## Join diagram

```mermaid
erDiagram
    final_album_df {
        int album_id PK
        string album_name
        int artist_credit FK
        float rating
        int rating_count
        int language
        string country
        int album_year
        int label_id
        int label_type
        dict album_tags
        dict label_tags
    }
    final_artist_df {
        int id PK
        string name
        int artist_year
        int type
        int area
        int gender
        float rating
        int rating_count
        dict artist_tags
    }
    master_df {
        int album_id PK
        string album_name
        int artist_credit FK
        float album_rating
        int album_rating_count
        string country
        int album_year
        int label_id
        dict album_tags
        dict label_tags
        int artist_year
        int artist_type
        float artist_rating
        dict artist_tags
    }

    final_album_df }o--|| final_artist_df : "artist_credit = id"
    final_album_df ||--|| master_df : "enriched into"
    final_artist_df ||--o{ master_df : "contributes artist fields"
```
