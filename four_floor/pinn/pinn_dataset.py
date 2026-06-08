import torch
from torch.utils.data import Dataset, DataLoader

class SHMDataset(Dataset):
    def __init__(self, psd, alpha, omega, mass_type):
        """
        psd: (N, freq_bins)
        alpha: (N, 4)
        omega: (N, 2)
        mass_type: (N,) -> 0 for Consistent, 1 for Lumped
        """
        self.psd = torch.tensor(psd, dtype=torch.float32)
        self.alpha = torch.tensor(alpha, dtype=torch.float32)
        self.omega = torch.tensor(omega, dtype=torch.float32)
        self.mass_type = torch.tensor(mass_type, dtype=torch.long) 

    def __len__(self):
        return len(self.psd)

    def __getitem__(self, idx):
        # Unsqueezing PSD to (1, freq_bins) for 1D-CNN input channel
        return {
            'psd': self.psd[idx], 
            'alpha_true': self.alpha[idx],
            'omega_peak': self.omega[idx],
            'mass_type': self.mass_type[idx]
        }

def create_dataloaders(train_psd, train_a, train_w, test_psd, test_a, test_w, batch_size, extra_data=None):
    if extra_data is None or 'mass_type' not in extra_data:
        raise ValueError("Multi-physics training requires 'mass_type' in extra_data.")

    train_m = extra_data['mass_type'][0]
    test_m = extra_data['mass_type'][1]

    train_dataset = SHMDataset(train_psd, train_a, train_w, train_m)
    test_dataset = SHMDataset(test_psd, test_a, test_w, test_m)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, test_loader