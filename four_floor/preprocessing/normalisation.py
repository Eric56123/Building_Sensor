import numpy as np

class PSDScaler:
    def __init__(self):
        """
        A custom Log-Min-Max Scaler designed specifically for Structural PSD data.
        It remembers the scaling bounds from the training data to safely apply to test data.
        """
        self.min_val = None
        self.max_val = None
        self.epsilon = 1e-10 # Prevents math domain errors from log10(0)

    def fit_transform(self, psd_training_data):
        """
        Use this ONLY on your Training Dataset.
        psd_training_data: numpy array of shape (N_samples, 4_sensors, N_bins)
        """
        # 1. Log-Scale to compress the orders of magnitude
        log_psd = np.log10(psd_training_data + self.epsilon)
        
        # 2. Find the global minimum and maximum across the entire training set
        self.min_val = np.min(log_psd)
        self.max_val = np.max(log_psd)
        
        # 3. Min-Max Scale strictly between 0.0 and 1.0
        scaled_data = (log_psd - self.min_val) / (self.max_val - self.min_val)
        
        print(f"Scaler fitted. Min: {self.min_val:.2f}, Max: {self.max_val:.2f}")
        return scaled_data

    def transform(self, psd_test_data):
        """
        Use this on your Testing Dataset or Real Field Data.
        It applies the saved training bounds to prevent data leakage.
        """
        if self.min_val is None or self.max_val is None:
            raise ValueError("Fatal Error: You must run fit_transform() on training data first!")
            
        # 1. Log-Scale
        log_psd = np.log10(psd_test_data + self.epsilon)
        
        # 2. Scale using the locked TRAINING boundaries
        scaled_data = (log_psd - self.min_val) / (self.max_val - self.min_val)
        
        # 3. Clip the data. If the real building experiences a wind gust larger than 
        # anything in the training set, this strictly enforces the 1.0 ceiling.
        return np.clip(scaled_data, 0.0, 1.0)

# ---------------------------------------------------------
# HOW TO USE THIS IN YOUR MAIN PIPELINE
# ---------------------------------------------------------
def prepare_tensors_for_pinn(all_psd_arrays, train_ratio=0.8):
    """
    Splits the data, applies the PSDScaler, and shapes it for PyTorch/TensorFlow.
    Assume all_psd_arrays is shape (Total_Samples, 4, N_bins)
    """
    total_samples = all_psd_arrays.shape[0]
    split_idx = int(total_samples * train_ratio)
    
    # 1. Split the raw data first (No Data Leakage!)
    train_psd_raw = all_psd_arrays[:split_idx]
    test_psd_raw = all_psd_arrays[split_idx:]
    
    # 2. Initialize the Scaler
    scaler = PSDScaler()
    
    # 3. Fit and Transform the Training Data
    train_psd_clean = scaler.fit_transform(train_psd_raw)
    
    # 4. Transform the Test Data (using the locked training bounds)
    test_psd_clean = scaler.transform(test_psd_raw)
    
    return train_psd_clean, test_psd_clean, scaler