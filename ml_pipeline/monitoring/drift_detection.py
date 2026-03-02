import subprocess
from drift_detection import detect_drift


def retrain_pipeline():

    print("Drift detected. Starting retraining...")

    subprocess.run(["python", "ml_pipeline/feature_engineering/build_training_dataset.py"])
    subprocess.run(["python", "ml_pipeline/training/train_model.py"])

    print("Retraining complete.")


if __name__ == "__main__":

    result = detect_drift()

    print("Drift Result:", result)

    if result.get("drift_detected"):
        retrain_pipeline()
    else:
        print("No significant drift detected.")