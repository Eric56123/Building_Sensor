# 9. Methodology

## 9.1 Overview and Research Design

Structural health monitoring (SHM) infers the condition of a structure from its measured dynamic response. The central aim of this project is an inverse problem: given the vibration response of a multi-storey frame, recover a set of per-storey stiffness retention factors $\alpha \in [0,1]$ that quantify damage, where $\alpha = 1$ denotes an intact storey and $\alpha = 0$ a complete loss of lateral stiffness. This is an ill-posed problem, because many distinct damage states can produce very similar responses [Zar et al., 2024]. The contribution of this work is to constrain the inversion using the governing physics of structural dynamics rather than data alone, addressing objective [OBJECTIVE — to be filled] (Section X): to recover localised stiffness loss from measured response data.

The approach is a physics-informed neural network (PINN). A convolutional–dense network maps the frequency-domain response of a structure to its per-storey stiffness parameters, while a physics-based loss term penalises solutions that are inconsistent with the modal eigenvalue problem,
$$(K(\alpha) - \omega_n^2 M)\,\Phi = 0.$$
The data loss anchors predictions to labelled examples, whereas the physics loss enforces dynamic feasibility of the recovered stiffness; the latter is expressed through a singular-value formulation (Section 9.4) in place of a conventional residual norm. This constraint operates during training and is embedded in the network weights, allowing rapid, single-pass damage estimation suitable for deployment on the target hardware.

The methodology is validated in stages. The network is first trained and tested on synthetic data generated from a forward structural-dynamics model, for which the stiffness state is known exactly. It is then evaluated on the Johnson et al. [2004] four-storey simulated benchmark, which serves as an out-of-distribution test because its damage patterns are not drawn from the training distribution. Finally, a physical sensor node built from an ADXL345 accelerometer and a Raspberry Pi 4 demonstrates the end-to-end pipeline on real hardware. The complete processing chain, from raw acceleration to damage classification, is summarised in Figure 2, with each stage detailed below.

## 9.2 Forward Structural-Dynamic Model

Training a network to solve the inverse problem requires a large set of response records for which the stiffness state is known exactly. Such labelling is not available from field measurements, so the training data are generated synthetically from a forward structural-dynamics model. This section describes that model: the idealisation of the structure, the parametrisation of damage, and the time-domain simulation used to produce acceleration records.

### 9.2.1 Structural Idealisation

The building is represented as a shear-building model, in which each floor is treated as a rigid diaphragm and the lateral storey stiffnesses are provided by the columns between floors. Following the Johnson et al. [2004] benchmark used for validation, each floor carries three degrees of freedom — two translational ($x$, $y$) and one rotational ($\theta$) — so the four-storey structure is a twelve-degree-of-freedom system, with mass and stiffness matrices of dimension $12 \times 12$. The equation of motion is
$$M\ddot{u}(t) + C\dot{u}(t) + K u(t) = f(t),$$
where $M$, $C$ and $K$ are the mass, damping and stiffness matrices, $u(t)$ is the displacement vector and $f(t)$ the applied force. The mass matrix $M$ is assembled from the floor masses; both consistent and lumped formulations were implemented, and the choice between them is treated as a source of modelling uncertainty (Section 9.2.6). The stiffness matrix $K$ is formed from the inter-storey stiffnesses given in Johnson et al. [2004].

The full twelve-degree-of-freedom system is retained throughout the forward simulation and the physics loss, so that the coupling between translation and rotation is preserved. The network, however, observes only the four $y$-direction translational responses — one per floor — as its input channels (Section 9.5), reflecting a realistic single-axis sensing arrangement, and predicts one retention factor per storey.

### 9.2.2 Damage Parametrisation

Damage is represented as a reduction in storey stiffness, following the standard SHM assumption that damage alters stiffness while leaving mass and damping essentially unchanged [Johnson et al., 2004]. Each storey is assigned a stiffness retention factor $\alpha_i \in [0,1]$, with $\alpha_i = 1$ an intact storey and $\alpha_i = 0$ a complete loss of lateral stiffness. The global stiffness matrix is a linear combination of the storey contributions,
$$K(\alpha) = \sum_{i=1}^{N} \alpha_i K_i,$$
where $K_i$ is the $12 \times 12$ contribution of storey $i$ to the global stiffness, obtained by decomposing the baseline stiffness matrix into its per-storey blocks. This is the central mathematical device of the methodology: it is differentiable and appears directly in the physics loss of Section 9.4, where the recovered $\hat{\alpha}$ is substituted back into the governing equations. Crucially, the same superposition is used to *generate* the training data (Section 9.2.5), so that each synthetic record has a stiffness state that lies exactly in the span of $\{K_i\}$ — a property the physics loss depends upon (Section 9.4.3).

### 9.2.3 Damping

To introduce damping, the generalised eigenvalue problem
$$K\Phi = M\Phi\,\Omega^2$$
is solved for the natural frequencies and mass-normalised mode shapes, where $\Phi$ is the modal matrix ($\Phi^{T} M \Phi = I$) and $\Omega^2$ is diagonal with entries $\omega_n^2$, the squared natural frequencies. A damping ratio $\zeta = 1\%$ is applied to each mode, giving the modal term $2\zeta\omega_n$, which is collected into a diagonal matrix to form the damping matrix
$$C = M\Phi\,\mathrm{diag}(2\zeta\omega_n)\,\Phi^{T} M.$$
This delivers the prescribed 1% damping to each mode. The construction was verified by displacing the structure into its first mode and confirming that the free-decay response follows the analytical envelope $e^{-\zeta\omega_n t}$ (Figure 3).

### 9.2.4 Excitation and Time Integration

Each structure is excited by Gaussian white noise, generated by passing white noise through a sixth-order Butterworth low-pass filter (20 Hz cut-off) and applied to the $y$-translational degrees of freedom. Because band-limited white noise covers the structural frequency range, it excites all modes of interest and approximates the ambient and shake-table conditions used elsewhere (Section X). The response is computed by Newmark-$\beta$ time integration in its constant-average-acceleration form ($\beta = 0.25$, $\gamma = 0.5$) [Newmark, 1959], which is unconditionally stable and therefore handles the stiffness reductions of severe damage cases. Simulations are run at a sampling frequency of 1000 Hz over 40 s. To emulate real instrumentation, Gaussian noise at 10% RMS of the signal is added to each acceleration record after simulation; every damage case is driven by an independent excitation and noise realisation, isolating the effect of damage from that of excitation variability.

### 9.2.5 Damage-Pattern Sampling

Because the network must learn a continuous four-dimensional inverse map, the training labels are drawn as continuously sampled $\alpha$ vectors rather than a small set of fixed patterns. Each $\alpha$ vector is drawn from a mixed prior designed to cover the $\alpha$ space densely while reflecting realistic monitoring conditions:

- **fully intact** ($\alpha = [1,1,1,1]$) — 20% of samples;
- **single-storey damage** — one storey's $\alpha_i$ drawn uniformly from $[0.2, 1.0]$, the rest intact — 50%;
- **multi-storey damage** — two to four storeys damaged, each $\alpha_i$ drawn uniformly from $[0.2, 1.0]$ — 30%.

Five hundred such $\alpha$ vectors are sampled. Each is simulated under both the consistent and lumped mass formulations, giving 1000 simulations; after windowing (Section 9.3) this yields 10,000 spectra spanning 401 distinct $\alpha$ vectors. This continuous sampling replaces an earlier scheme built on a handful of fixed benchmark patterns, which contained too few distinct $\alpha$ vectors to define a continuous inverse map — the network memorised the small set of labels it had seen rather than learning to generalise. The 20% intact fraction keeps the network sensitive to the undamaged state without biasing it toward predicting "intact everywhere", a failure mode to which a mean-absolute-error objective is otherwise vulnerable when most storeys are near-intact.

### 9.2.6 Assumptions and Sources of Uncertainty

Several assumptions underlie the model and are carried forward as caveats on the results. The shear-building idealisation assumes rigid floors and neglects axial and out-of-plane behaviour. Damage is assumed to arise only through stiffness reduction, with mass and damping held constant. The modal damping ratio is fixed at 1%, whereas real structures exhibit amplitude- and frequency-dependent damping. The choice between consistent and lumped mass formulations introduces a modelling uncertainty that propagates into the simulated frequencies, and is treated as an uncertainty rather than by assuming a single "correct" model. Finally, because the training data are generated from the same storey superposition $K(\alpha) = \sum_i \alpha_i K_i$ that the physics loss assumes, the synthetic study is internally consistent by construction; the Johnson et al. [2004] benchmark is retained specifically to probe robustness when the true stiffness state does *not* lie exactly in this span (Section 9.4.3).

## 9.3 Signal Processing and Feature Extraction

The forward model of Section 9.2 produces raw acceleration time-series for each damage case. These cannot be passed directly to the network; they are first transformed into a compact frequency-domain representation suited to training.

### 9.3.1 From Time Series to Frequency Domain

A raw acceleration record is a long, high-dimensional sequence — at 1000 Hz over 40 s, each channel contains 40,000 samples — in which damage information is not localised in time but distributed across the structure's resonant frequencies. Presenting such a sequence to a network is inefficient: the input dimension is large, and two records from the same damage state but different noise realisations look entirely different sample-by-sample while being physically equivalent. The signature of damage is instead a shift in the structure's resonant peaks, a property of the signal's frequency content rather than its time history.

The acceleration records are therefore converted to power spectral densities (PSDs) using Welch's method [Welch, 1967]. Welch's method divides the record into overlapping segments, computes a windowed periodogram of each, and averages them, reducing the variance of the spectral estimate. This averaging matters because the simulated records contain measurement noise, and a single periodogram would be too noisy to expose the resonant peaks clearly. Each 40 s record is first divided into non-overlapping windows of 4000 samples (4 s), giving ten spectra per simulation and providing multiple independent views of the same damage state. The PSD of each window is computed with a segment length of $n_\text{perseg} = 2048$, which at $f_s = 1000$ Hz yields 1025 frequency bins spanning 0–500 Hz. The resonant peaks and their movement under damage are preserved in this representation, while phase information and noise are suppressed. The observed fundamental frequency ranges from approximately 4.8 to 9.4 Hz across the sampled damage states, well within the retained band.

### 9.3.2 Normalisation

PSD magnitudes span several orders of magnitude — the power at resonant peaks can exceed that of the surrounding spectrum by orders of magnitude — so the raw PSD is unsuitable as a network input: the large dynamic range produces ill-conditioned gradients and lets a few high-power bins dominate training. The PSD is therefore compressed logarithmically and rescaled to a fixed range. Each PSD is transformed as $\log_{10}(\text{PSD} + \epsilon)$, with $\epsilon = 10^{-10}$ preventing the logarithm of zero in bins of negligible power. The logarithmic values are then linearly rescaled to $[0,1]$ using fixed bounds determined from the training set,
$$P = \mathrm{clip}\!\left(\frac{\log_{10}(\text{PSD} + \epsilon) - P_\text{min}}{P_\text{max} - P_\text{min}},\, [0,1]\right),$$
where $P_\text{min}$ and $P_\text{max}$ are the lower and upper log-PSD bounds and the clip operation caps values outside $[0,1]$. These bounds are computed once from the training partition and stored; the identical bounds are reused at inference and are never recomputed per record, so that any new record — including one from the sensor node — is presented to the network on exactly the scale it was trained on. In the reported runs $P_\text{min} = -10.0$ (set by the $\epsilon$ floor) and $P_\text{max} \approx -1.7$; the upper bound is data-dependent and is refitted whenever the training partition changes. The logarithmic compression brings the resonant peaks and the spectral floor into a comparable numerical range, and the fixed rescaling keeps the network's inputs bounded and its gradients well-conditioned.

## 9.4 The Physics-Informed Loss

As described so far, the network is a conventional data-driven regressor: it learns to map PSDs to stiffness parameters from labelled examples alone. What makes it physics-informed is an additional loss term that penalises predictions inconsistent with the governing equations, independent of the training labels. This is a parameter-identification PINN: the network outputs a physical parameter $\alpha$ rather than a solution field, so the physics is used not to solve the equations of motion but to test whether a predicted stiffness state is dynamically consistent with the structure's observed resonances.

### 9.4.1 The Physics Residual

The undamped modal behaviour of the structure is governed by the eigenvalue problem of Section 9.1,
$$(K(\alpha) - \omega_n^2 M)\,\phi_n = 0,$$
where $\omega_n$ and $\phi_n$ are the $n$-th natural frequency and mode shape. For this equation to admit a non-trivial mode shape ($\phi_n \neq 0$), the matrix $(K(\alpha) - \omega_n^2 M)$ must be singular at each natural frequency $\omega_n$. This provides a direct test of a predicted stiffness state: if the predicted $\hat{\alpha}$ is correct, substituting it into $(K(\hat{\alpha}) - \omega_n^2 M)$ at each measured resonant frequency yields a singular — or nearly singular — matrix, whereas an incorrect $\hat{\alpha}$ leaves the matrix non-singular at those frequencies. The degree of singularity measures how well a prediction respects the structure's measured dynamics, and this is the quantity the physics loss minimises.

### 9.4.2 Why the Frobenius Norm Fails

The apparent way to quantify how nearly the residual matrix satisfies the eigenvalue problem is to take its Frobenius norm — effectively the root-sum-of-squares of all entries. This was the initial choice, and it did not work. The failure was one of scale: the stiffness matrix $K$ is numerically dominant, while the modal term $\omega_n^2 M$, which carries the frequency information, contributes only a small fraction of the matrix's total magnitude. The Frobenius norm is therefore largely a measure of the size of $K$, which barely changes as $\hat{\alpha}$ varies, and is almost insensitive to the modal term that captures damage. As a result the loss was nearly constant across predictions, producing small gradients and giving the optimiser almost no signal to descend — so the physics term contributed essentially nothing to training.

### 9.4.3 The Singular-Value Formulation

The adopted method measures singularity directly through the singular values of the residual matrix. The smallest singular value $\sigma_\text{min}$ of a matrix is zero exactly when the matrix is singular, so the physics loss is defined as the ratio of the smallest to the largest singular value of the residual,
$$L_\text{phys} = \frac{\sigma_\text{min}\big(K(\hat{\alpha}) - \omega_n^2 M\big)}{\sigma_\text{max}\big(K(\hat{\alpha}) - \omega_n^2 M\big)}.$$
This is evaluated at each measured resonant frequency, summed over the measured modes, and averaged across the batch. Dividing by $\sigma_\text{max}$ normalises the measure, so the loss reports how close to singular the matrix is rather than its absolute size — the sensitivity the Frobenius norm lacked — and confines it to $[0,1]$.

A decisive requirement of this formulation is that the true stiffness state must lie in the span of the storey superposition $K(\alpha) = \sum_i \alpha_i K_i$. When it does, the residual is exactly singular at the true $\alpha$ and $L_\text{phys}$ reaches zero — measured at order $10^{-8}$ on the synthetic data, whose labels are generated from precisely this superposition (Section 9.2.5). The loss then has a well-defined descent target at the correct answer. This condition is not automatic: a damage state expressed outside the span — for example a stiffness matrix reduced by an independent process, as in the Johnson et al. [2004] benchmark — cannot be represented exactly by any $\alpha$, so the residual retains a non-zero floor and $L_\text{phys}$ no longer vanishes at the true state. The physics term is therefore only as informative as the fidelity of the storey-superposition model, a limitation examined directly in the benchmark evaluation (Section 10).

The physics loss is applied as a soft regularisation term rather than a hard constraint: because labelled simulation data supply a strong primary training signal, the physics term's role is to bias the network toward dynamically consistent solutions that the data alone cannot distinguish — particularly valuable when many stiffness states can produce similar responses. The relative weighting of the two terms is discussed in Section 9.6, and its empirical effect is reported in Section 10.

## 9.5 Neural Network Architecture

The network maps a preprocessed frequency-domain input to a vector of per-storey stiffness parameters. It combines a convolutional feature extractor, which identifies spectral patterns associated with damage, with a fully-connected regressor that maps those features to stiffness estimates. It is implemented for the four-storey case, with an $N$-storey generalisation described as a designed extension below.

### 9.5.1 Input Representation

The input is the normalised log-PSD tensor of Section 9.3, of shape $(4, 1025)$: four channels, one per floor, each a 1025-bin spectrum. Treating each floor as a separate channel lets the convolutional layers learn features across floors while preserving the frequency structure along each spectrum.

### 9.5.2 Convolutional Feature Extractor

Because the spectral signatures of damage appear as shifts in resonant peaks — local patterns in frequency — a one-dimensional convolutional network is well suited to detecting them. The feature extractor applies three 1D convolutional blocks with kernel sizes 5, 5 and 3: the wider early kernels capture broad spectral structure, while the final narrower kernel resolves finer detail. Each convolution is followed by batch normalisation and a ReLU activation, the former stabilising and accelerating training by rescaling each layer's activations — useful given the wide range of spectral inputs. A max-pooling layer follows each of the first two blocks, halving the sequence length and progressively condensing the spectral representation before the final convolution. The channel depth increases through the stack ($4 \to 16 \to 32 \to 64$), so each layer represents a greater number of learned spectral features. Because the convolutional output depends on the input spectrum length, an adaptive average-pooling layer follows the final convolution, pooling each of the 64 feature channels to a fixed size of 16 and producing a feature map of $64 \times 16 = 1024$ regardless of input length. This is what allows the same network to accept spectra of differing lengths without redesign, and it is central to the $N$-storey generalisation below.

### 9.5.3 Regressor

The flattened 1024-dimensional feature vector is passed through a multi-layer perceptron with three hidden widths of 256, 128 and 64, each followed by a ReLU activation. Dropout with probability 0.2 is applied after the first two hidden layers during training, randomly deactivating a fraction of units to reduce over-fitting to the synthetic training distribution. The final layer produces one output per storey, each passed through a sigmoid activation. The sigmoid constrains every output to $(0,1)$, enforcing $\alpha \in [0,1]$ by construction: the network cannot predict a physically meaningless negative stiffness or a value above the intact state. The physical constraint is thus an architectural guarantee rather than something the loss must learn.

### 9.5.4 Generalisation to N Storeys

The architecture is designed to extend beyond four storeys without redesign. The adaptive pooling layer fixes the feature dimension irrespective of input length, and a variable-height input is accommodated by zero-padding each record to a common channel count $N_\text{max}$ together with a floor mask that identifies the physical storeys. The same masking would be used in the data loss (Section 9.6) so that padded channels contribute nothing to training. This extension is presented as a designed capability; only the four-storey case is implemented and validated in this work, and full $N$-storey validation is left to future work.

### 9.5.5 Architecture Summary

The full architecture is summarised in Figure 5 and Table 1.

**Table 1.** Layer-by-layer architecture of the four-storey network. Output shapes are (channels, length) for convolutional stages and (features) for dense stages, for a single input of shape (4, 1025).

| Stage | Layer | Output shape | Parameters |
|---|---|---|---|
| Input | – | (4, 1025) | – |
| Conv block 1 | Conv1d (k=5) + BN + ReLU + MaxPool | (16, 512) | 368 |
| Conv block 2 | Conv1d (k=5) + BN + ReLU + MaxPool | (32, 256) | 2,656 |
| Conv block 3 | Conv1d (k=3) + BN + ReLU | (64, 256) | 6,336 |
| Pooling | AdaptiveAvgPool1d(16) | (64, 16) | – |
| Flatten | – | (1024) | – |
| Dense 1 | Linear + ReLU + Dropout (p=0.2) | (256) | 262,400 |
| Dense 2 | Linear + ReLU + Dropout (p=0.2) | (128) | 32,896 |
| Dense 3 | Linear + ReLU | (64) | 8,256 |
| Output | Linear + Sigmoid | (4) | 260 |
| **Total** | | | **313,172** |

*(Figure 5 note: the convolutional kernel sizes shown must read 5, 5, 3 to match Table 1 and the text.)*

## 9.6 Training Procedure

The network is trained by minimising a composite objective that combines a data-fidelity term with the physics residual of Section 9.4,
$$\mathcal{L} = \mathcal{L}_\text{data} + \lambda\,\mathcal{L}_\text{phys},$$
where $\mathcal{L}_\text{data}$ measures agreement between the predicted and true stiffness retention factors and $\mathcal{L}_\text{phys}$ penalises predictions that are dynamically inconsistent with the measured resonances. The weight $\lambda$ controls how strongly the physics term regularises the data fit; a value of $\lambda = 0.1$ is used throughout, selected from the sweep reported in Section 10.

The data term is a mean-squared error over the per-storey outputs,
$$\mathcal{L}_\text{data} = \frac{1}{\sum_i m_i}\sum_{i=1}^{N_\text{max}} m_i\,(\hat{\alpha}_i - \alpha_i)^2,$$
where $m_i \in \{0,1\}$ is a floor mask that is one for a physical storey and zero for a zero-padded channel. For the four-storey study every channel is physical, so the mask is uniformly one and the term reduces to a plain mean-squared error; the masked form is written here because it is the objective intended for the $N$-storey extension (Section 9.5.4), in which inputs of differing height may share a batch and padded channels must contribute neither to the loss nor to its gradient.

Both terms are dimensionless and bounded: the data error is a mean square of quantities in $[0,1]$, and the physics ratio of Section 9.4 lies in $[0,1]$ by construction. They are therefore already of comparable scale, so $\lambda$ sets the relative magnitude of their gradients rather than correcting a unit mismatch. Near convergence the data term settles to order $\sim\!2\times10^{-4}$ and the unweighted physics term to order $\sim\!3\times10^{-4}$; with $\lambda = 0.1$ the weighted physics contribution is $\sim\!3\times10^{-5}$, roughly one-eighth of the data term, so it biases the solution toward dynamic consistency without overriding the label information. The sensitivity of performance to $\lambda$ is reported in Section 10.

The resonant frequencies $\omega_n$ entering the physics loss are those of the true damage case, obtained from the forward eigenproblem of Section 9.2.3 and stored alongside each synthetic record. The predicted $\hat{\alpha}$ is substituted into $(K(\hat{\alpha}) - \omega_n^2 M)$ at these frequencies and the smallest-to-largest singular-value ratio is evaluated over the first two modes. Because the singular-value decomposition is differentiable, this term contributes gradients to $\hat{\alpha}$ through the network weights. A per-sample mass matrix is selected according to whether the record was simulated under the consistent or lumped formulation, so the physics residual is evaluated against the mass model that actually produced the data.

Parameters are updated with the Adam optimiser at an initial learning rate of $5\times10^{-4}$, decayed by a cosine-annealing schedule ($\eta_\text{min} = 10^{-6}$) over a fixed budget of 200 epochs; no early stopping is used, and the final-epoch weights are retained. Cosine annealing lowers the rate smoothly toward the end of training, permitting large early steps for rapid descent and small late steps to settle into a minimum without manual step scheduling. No weight decay is applied. Gradients are clipped to a maximum norm of 1.0 before each optimiser step, which guards against the ill-conditioned gradients that the singular-value decomposition can produce when the residual matrix is close to singular.

Training uses a batch size of 16 with ordinary shuffled batching. (A `FloorCountBatchSampler`, which would group samples of equal storey count $N$ into each batch so that the fixed-dimension singular-value decomposition can be batched without conditional branching on $N$, is part of the planned $N$-storey extension; for the four-storey study all samples share $N = 4$ and shuffled batching suffices.)

The synthetic dataset is partitioned by *damage pattern*, not by individual window. Because each $\alpha$ vector contributes multiple windows and appears under two mass formulations, splitting at the window level would place near-identical spectra of the same $\alpha$ in both training and test sets, leaking information and inflating apparent accuracy. Instead, both mass variants and all windows of a given $\alpha$ are held out together: of the 500 sampled $\alpha$ vectors, 400 (8000 windows) are used for training and 100 (2000 windows) for testing, so that every test $\alpha$ is genuinely unseen. The PSD normalisation bounds (Section 9.3.2) are refitted on each fold's training partition only. The same grouped partitioning underlies the $k$-fold cross-validation reported in Section 10. Because the singular-value decomposition is unimplemented on the PyTorch MPS (Apple GPU) backend, that operation falls back to the CPU; the decomposition is nevertheless batched across the whole mini-batch in a single call, which keeps the fallback tractable, and a full 200-epoch run completes in approximately 20 minutes on the target machine.

## 9.7 Inference and Evaluation Pipeline

Once trained, the network is applied to data it has not seen — held-out synthetic cases, the Johnson et al. [2004] benchmark, and records from the hardware node — and its predictions are turned into a damage decision. To keep every input on the same footing as the training data, each new record passes through the identical preprocessing chain used during training.

A raw record is first detrended to remove any mean offset and slow drift, then bandpass filtered to the structural band of 0.5–45 Hz to suppress out-of-band thermal drift and electrical-mains interference while retaining the structure's modes (which lie below about 10 Hz). Its power spectral density is estimated by Welch's method with the same segment length used in training; where a record's native sampling rate differs from the 1000 Hz of the synthetic data, the spectrum is expressed on the common 1025-bin, 0–500 Hz frequency axis so that records acquired at different rates map onto the same input representation. The spectrum is then log-compressed and rescaled using the stored $P_\text{min}$ and $P_\text{max}$ bounds from training — not recomputed per record — so that magnitudes map onto exactly the scale the network was trained on. The preprocessed tensor is passed through the network in a single forward pass to produce the per-storey estimates $\hat{\alpha}$, which are mapped to a discrete damage status (indicated on the hardware node by the LED) using thresholds on $\hat{\alpha}$ [thresholds — to be filled].

*(Consistency note: this chain uses the same 1025-bin, 0–500 Hz Welch representation as Sections 9.3 and 9.5; the earlier draft's separate "0–15 Hz interpolation grid" has been removed so that Figure 2, Section 9.3, Section 9.5 and this section describe a single, common input representation.)*

Records from the physical sensor node require two additional steps before this common chain. Adaptive active-window detection first isolates the excited segment of the record from ambient or idle portions, so that the PSD is estimated over genuine structural response rather than background noise. Each measurement is then assigned to a floor by the channel-to-floor mapping: with a single roving accelerometer deployed under the sequential single-sensor protocol, the floor label follows the sensor's position for that recording. [Sensor-pair averaging — confirm whether this belongs here or in future work.]

Performance is evaluated against the known stiffness state on the synthetic and benchmark data using per-storey mean absolute error in $\hat{\alpha}$; localisation — whether the smallest predicted $\hat{\alpha}$ falls on the genuinely weakest storey, against a chance level of 0.25 for four storeys; and detection — whether a damaged state is correctly distinguished from an intact one. Two baselines are reported alongside these metrics to guard against the misleading optimism of mean absolute error when most storeys are near-intact: a *trivial* predictor that always returns $\alpha = 1$, and a *mean* predictor that always returns the training-set average. A model is only meaningful if it beats both. Monotonicity — whether $\hat{\alpha}$ decreases consistently as true severity increases — is also examined. For the hardware demonstration, where no exact ground truth is available, validation is qualitative and progressive: the criterion is a monotonic decrease of $\hat{\alpha}$ at the damaged floor with correct localisation. Numerical results are reported in Section 10.
