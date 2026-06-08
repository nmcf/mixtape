# Schema Diagrams

Visual reference for how the Parquet tables relate to each other and how they are combined into the training pipeline.

## Raw Parquet table relationships

```mermaid
erDiagram
    mb_artist {
        int id PK
        string name
        int artist_year
        int type
        int area
        int gender
    }
    mb_artist_tag {
        int artist_id FK
        int tag_id
        int tag_count
    }
    mb_artist_ratings {
        int artist_id PK
        float rating
        int rating_count
    }
    mb_artist_credit {
        int artist_credit PK
        string name
        int artist_count
        int ref_count
        int position
        int artist_id FK
        string artist_name
        string join_phrase
    }
    mb_album {
        int id PK
        string name
        int artist_credit FK
    }
    mb_album_tag {
        int album_id FK
        int tag_id
        int tag_count
    }
    mb_album_ratings {
        int album_id PK
        float rating
        int rating_count
    }
    mb_album_country {
        int album_id PK
        int language
        string country
        int album_year
    }
    mb_album_label {
        int album_id FK
        int label_id
        int label_type
        int tag_id
        int tag_count
    }
    mb_album_artists {
        int album_id PK
        string album_name
        int artist_id FK
        string artist_name
    }

    mb_artist ||--o{ mb_artist_tag : "artist_id"
    mb_artist ||--o| mb_artist_ratings : "artist_id"
    mb_artist ||--o{ mb_artist_credit : "artist_id"
    mb_album }o--|| mb_artist_credit : "artist_credit"
    mb_album ||--o{ mb_album_tag : "album_id"
    mb_album ||--o| mb_album_ratings : "album_id"
    mb_album ||--o| mb_album_country : "album_id"
    mb_album ||--o{ mb_album_label : "album_id"
    mb_album ||--o| mb_album_artists : "album_id"
    mb_artist ||--o| mb_album_artists : "artist_id"
```

## Dataset construction joins

How the parquet tables are combined in `datasets/parquet-dataframes.ipynb`:

```mermaid
flowchart TB
    subgraph Album side
        A[mb_album] --> FA
        AR[mb_album_ratings] --> FA
        AC[mb_album_country] --> FA
        AL[mb_album_label] --> FA
        AT[mb_album_tag] -->|grouped dict| AT2[album_tag_dict]
        AT2 --> FA
        AL -->|grouped dict| LT[label_tag_dict]
        LT --> FA
        FA[final_album_df]
    end

    subgraph Artist side
        B[mb_artist] --> FB
        BR[mb_artist_ratings] --> FB
        BT[mb_artist_tag] -->|grouped dict| BT2[artist_tag_dict]
        BT2 --> FB
        FB[final_artist_df]
    end

    FA -->|join on artist_credit = id| M[master_df]
    FB -->|join on artist_credit = id| M
```

## Feature matrix construction

How `final_album_df` and supporting tables feed into the feature matrices:

```mermaid
flowchart LR
    subgraph Inputs
        AT[album_tags_matrix.npz]
        AL[album_labels_matrix.npz]
        TY[album_types_matrix.npz]
        RT[album_ratings_matrix.npz]
    end

    subgraph Preprocessing
        AT --> EX[Expand to full universe]
        AL --> EX
        TY --> EX
        RT --> EX
        EX --> HS[hstack]
        HS --> PR[Prune low-signal cols]
        PR --> NR[L2 normalise]
    end

    subgraph Model
        NR --> KNN[NearestNeighbors fit]
        KNN --> MF[knn_model.joblib]
        NR --> MX[X_knn_norm.npz]
    end
```

## App data flow

```mermaid
flowchart TD
    U[User: artist name] --> S[search_artist]
    S --> LK[mb_album_artists lookup]
    LK --> DD[Album dropdown filtered to recommendable albums]
    DD --> R[recommend function]
    R --> MX[X_knn_norm.npz]
    MX --> KNN[knn_model.joblib]
    KNN --> RES[Top-N results]
    RES --> LK2[Enrich with album/artist names]
    LK2 --> UI[Display table]
```
