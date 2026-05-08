# SURAKSHA Backend

FastAPI backend for the SURAKSHA behavioral authentication demo.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at:

- Health check: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`

## API Contract

### `POST /predict`

Request:

```json
{
  "mouse": [
    { "x": 120, "y": 300, "t": 0 }
  ],
  "keyboard": [
    { "key": "a", "down": 100, "up": 180 }
  ],
  "device": {
    "userAgent": "Mozilla/5.0 ...",
    "screen": [1920, 1080],
    "timezone": "Asia/Kolkata"
  }
}
```

Response:

```json
{
  "is_human": true,
  "risk_score": 0.82,
  "message": "Low Risk - Access Granted"
}
```

Current demo scoring uses feature extraction plus simple rules. The trained ML model will be added later.

## Sample Payloads

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  --data @samples/human_payload.json

curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  --data @samples/bot_payload.json
```

## Generate Bot Dataset

```bash
python scripts/generate_bot_data.py -n 3000 --seed 2202
```

This creates:

```txt
data/raw/bot_data.json
```

Each generated session contains `mouse`, `keyboard`, `device`, and `label`, where `label` is `0` for bot.

## Generate Human Dataset

Synthetic human sessions:

```bash
python scripts/generate_synthetic_human_data.py -n 2000 --seed 1101
```

Augmented human sessions:

```bash
python scripts/augment_data.py \
  --input data/raw/human_synthetic_data.json \
  --output data/raw/human_augmented_data.json \
  --multiplier 4 \
  --seed 3303
```

Convert public datasets:

```bash
python scripts/convert_public_datasets.py \
  --max-cmu 3000 \
  --max-balabit 3000 \
  --seed 303
```

The converter expects these downloaded sources:

```txt
/Users/kumar/Downloads/DSL-StrongPasswordData.csv
/Users/kumar/Downloads/Mouse-Dynamics-Challenge-master
```

Merge final raw dataset:

```bash
python scripts/merge_raw_datasets.py --seed 4404 --label-noise 0.02
```

Import recorded human sessions:

```bash
python scripts/import_recorded_human_data.py
python scripts/augment_data.py \
  --input data/raw/recorded_human_data.json \
  --output data/raw/recorded_human_augmented_data.json \
  --multiplier 8 \
  --profile recorded \
  --seed 606
python scripts/merge_raw_datasets.py --seed 4404 --label-noise 0.02
```

Current generated counts:

```txt
human_synthetic_data.json   2,000 human sessions
human_augmented_data.json   8,000 human sessions
public_human_data.json      6,000 human sessions
recorded_human_data.json      104 human sessions
recorded_human_augmented_data.json
                              832 human sessions
bot_data.json               3,000 bot sessions
final_session_dataset.json 19,936 total sessions
```

## Current Structure

```txt
backend/
  app/
    __init__.py
    features.py
    main.py
    schemas.py
  samples/
    bot_payload.json
    human_payload.json
  scripts/
    augment_data.py
    convert_public_datasets.py
    dataset_common.py
    generate_bot_data.py
    generate_synthetic_human_data.py
    import_recorded_human_data.py
    merge_raw_datasets.py
  data/
    external/
      balabit/
      cmu_keystroke/
    processed/
    raw/
      bot_data.json
      final_session_dataset.json
      human_augmented_data.json
      human_synthetic_data.json
      public_human_data.json
      recorded_human_augmented_data.json
      recorded_human_data.json
  requirements.txt
  README.md
```
