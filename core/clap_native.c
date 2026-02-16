/*
 * clap_native.c — High-performance clap detection kernel
 * Compiled to clap_native.dll, called from Python via ctypes.
 *
 * Exports:
 *   int analyze_clap(float* samples, int n_samples, int samplerate,
 *                    float threshold, float noise_floor, float clap_ratio,
 *                    float prev_energy, float onset_ratio, float hf_ratio_min,
 *                    float* out_energy, float* out_new_noise_floor)
 *
 * Returns 1 if clap detected, 0 otherwise.
 * Writes computed energy to *out_energy and updated noise_floor to *out_new_noise_floor.
 */

#include <math.h>

#ifdef _WIN32
  #define EXPORT __declspec(dllexport)
#else
  #define EXPORT __attribute__((visibility("default")))
#endif

/*
 * Compute RMS energy of a float buffer, scaled by 100 (matching Python version).
 */
static float compute_rms(const float* samples, int n) {
    double sum = 0.0;
    for (int i = 0; i < n; i++) {
        sum += (double)samples[i] * (double)samples[i];
    }
    return (float)(sqrt(sum / n) * 100.0);
}

/*
 * Compute high-frequency energy ratio using a partial DFT.
 * Instead of a full FFT, we compute energy in two bands:
 *   - Low band:  bins 0 .. split-1
 *   - High band: bins split .. n_bins-1
 * where n_bins = n_samples/2 + 1 and split = n_bins/4.
 *
 * For 512 samples this is only ~128 bins total, with the split at bin 32.
 * We compute the magnitude squared for each bin via DFT:
 *   X[k] = sum_{n=0}^{N-1} x[n] * e^{-j*2*pi*k*n/N}
 *   |X[k]|^2 = Re(X[k])^2 + Im(X[k])^2
 *
 * Optimization: we only compute bins in each band and accumulate energy.
 */
static float compute_hf_ratio(const float* samples, int n_samples) {
    int n_bins = n_samples / 2 + 1;
    if (n_bins <= 4) return 0.0f;

    int split = n_bins / 4;
    if (split < 2) split = 2;

    double low_energy = 0.0;
    double high_energy = 0.0;
    double two_pi_over_n = 6.283185307179586 / (double)n_samples;

    /* Low band: bins 0..split-1 */
    for (int k = 0; k < split; k++) {
        double re = 0.0, im = 0.0;
        double w = two_pi_over_n * (double)k;
        for (int n = 0; n < n_samples; n++) {
            double angle = w * (double)n;
            re += (double)samples[n] * cos(angle);
            im -= (double)samples[n] * sin(angle);
        }
        low_energy += re * re + im * im;
    }

    /* High band: bins split..n_bins-1 */
    for (int k = split; k < n_bins; k++) {
        double re = 0.0, im = 0.0;
        double w = two_pi_over_n * (double)k;
        for (int n = 0; n < n_samples; n++) {
            double angle = w * (double)n;
            re += (double)samples[n] * cos(angle);
            im -= (double)samples[n] * sin(angle);
        }
        high_energy += re * re + im * im;
    }

    double total = low_energy + high_energy;
    if (total <= 0.0) return 0.0f;
    return (float)(high_energy / total);
}

/*
 * Main analysis function — called once per audio block (~23ms at 22050Hz).
 *
 * Parameters:
 *   samples         - float audio samples (mono)
 *   n_samples       - number of samples in the block
 *   samplerate      - sample rate (unused, for future use)
 *   threshold       - minimum energy to consider (e.g. 12)
 *   noise_floor     - current adaptive noise floor
 *   clap_ratio      - signal must be this many times above noise floor
 *   prev_energy     - energy from the previous audio block
 *   onset_ratio     - required energy jump ratio for transient detection
 *   hf_ratio_min    - minimum high-frequency energy ratio
 *   noise_alpha     - smoothing factor for noise floor update
 *   out_energy      - [output] computed energy of this block
 *   out_new_noise   - [output] updated noise floor
 *
 * Returns: 1 if clap detected, 0 otherwise.
 */
EXPORT int analyze_clap(
    const float* samples, int n_samples, int samplerate,
    float threshold, float noise_floor, float clap_ratio,
    float prev_energy, float onset_ratio, float hf_ratio_min,
    float noise_alpha,
    float* out_energy, float* out_new_noise
) {
    /* Step 1: RMS energy */
    float energy = compute_rms(samples, n_samples);
    *out_energy = energy;

    /* Update noise floor with quiet frames */
    if (energy < threshold * 0.5f) {
        *out_new_noise = (1.0f - noise_alpha) * noise_floor + noise_alpha * energy;
    } else {
        *out_new_noise = noise_floor;
    }

    /* Step 2: Above noise floor check */
    int above_noise = (energy > noise_floor * clap_ratio) && (energy > threshold);
    if (!above_noise) return 0;

    /* Step 3: Transient onset check */
    int onset;
    if (prev_energy > 0.01f) {
        float prev_safe = prev_energy > 0.01f ? prev_energy : 0.01f;
        onset = (energy / prev_safe) > onset_ratio;
    } else {
        onset = energy > (threshold * 2.0f);
    }
    if (!onset) return 0;

    /* Step 4: High-frequency ratio (only if first two checks pass — saves CPU) */
    float hf_ratio = compute_hf_ratio(samples, n_samples);
    return hf_ratio >= hf_ratio_min ? 1 : 0;
}
