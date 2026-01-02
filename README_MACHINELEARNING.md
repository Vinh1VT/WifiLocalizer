# Machine Learning Implementation

This branch uses machine learning to locate where a frame was taken. The algorithmic method (weighted average) is also available in this branch for comparison purposes.

## Usage

As the database must now contain 2 sets of coordinates (1 for the algorithmic method and 1 for the machine learning method), the database columns must be updated.

### Prerequisites

Ensure you have the necessary libraries installed (TensorFlow and Scikit-Learn).

### Steps

1. **Collect data**: Ensure you have enough data with GPS coordinates in your database.
2. **Train the model**: Run the training script `MachineLearning/model.py` to generate the `wifi_model.keras` file.
3. **Patch the database**: Run the patch script `patch_db.py`. This will add the new columns to the database AND use the generated model to calculate positions for existing historical data.
4. **Run the server**: Start the server as you would in the main branch.

> **Note :** On the map, you will now see the difference between the two methods' predictions.

---

## Continuous Improvement

If you collect new data, you can regenerate the model with better accuracy by running the training script again. Then, run the patch script to update the predictions in the database.

