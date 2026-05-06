# mixtape

What is
We want to connect music lovers with Albums and Artists.
Based on what you input we will output a list fo albums that you might want to check out.

## MVP Features
Input: list of Bands
Output: List of albums

## V2 Features

Web app - Steamlit
Rating feedback loop
Spotify API
Playlist
Filters:
- year of release
- Include listed Artist
- Genre
- Album name

- id,artist_credit_id,artist_mbids,artist_credit_name,release_mbid,release_name,recording_mbid,recording_name,combined_lookup,score

Setup
### 1. Database Prerequisite
This project requires a local instance of the MusicBrainz database running in Docker. Ensure your container is active and accessible at `localhost:5432`.

### 2. Create Python Environment
It is recommended to use a virtual environment to manage dependencies:

```bash
# Create the environment
python3 -m venv env

# Activate the environment
# On macOS/Linux:
source env/bin/activate
# On Windows:
# .\env\Scripts\activate

### 3. Install Dependencies
pip install -r requirements.txt