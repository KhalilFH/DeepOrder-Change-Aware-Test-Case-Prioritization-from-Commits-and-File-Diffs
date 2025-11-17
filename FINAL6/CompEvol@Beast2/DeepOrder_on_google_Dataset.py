#!/usr/bin/env python
# coding: utf-8

# ## 1. Importing Libraries and Setup

# CRITICAL: Configure TensorFlow BEFORE importing to avoid compilation errors
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TF logging
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'  # Dynamic GPU memory
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices=false'  # Disable XLA compilation
# Force CPU-only mode to avoid GPU compilation issues (libdevice.10.bc missing)
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # This forces TensorFlow to use CPU only
# Prevent loading CUDA libraries entirely to avoid double-free error
os.environ['LD_PRELOAD'] = ''  # Clear any preloaded libraries
print("⚠️  Running in CPU-only mode to avoid GPU compilation issues")

import pandas as pd
import numpy as np
from statistics import mean, stdev
from matplotlib import pyplot as plt
import seaborn as sns
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Lambda
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import backend as K
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from datetime import datetime
import warnings

warnings.simplefilter(action='ignore')
print(f"TensorFlow version: {tf.__version__}")

# Configure GPU for dynamic memory growth (avoids common errors)
# XLA JIT compilation already disabled at import time
tf.config.optimizer.set_jit(False)  # Additional JIT disabling for safety

gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"✅ GPU configured: {len(gpus)} GPU(s) available with dynamic memory growth")
    except RuntimeError as e:
        print(f"⚠️  GPU configuration warning: {e}")
        print("   Continuing with default GPU settings...")
else:
    print("ℹ️  No GPU detected. Using CPU for training (slower but stable).")

# --- Plotting Style ---
sns.set_context('paper', font_scale=1.5)
sns.set_palette(sns.color_palette("Set1", n_colors=8, desat=.5))
sns.set_style('whitegrid')

startTime = datetime.now()

# ## 2. Helper Functions

# --- Custom Activation Function: Mish ---
# Removed @tf.function decorator to avoid JIT compilation issues
def mish(inputs):
    return inputs * tf.nn.tanh(tf.nn.softplus(inputs))

# --- Custom Metric: Soft Accuracy ---
def soft_acc(y_true, y_pred):
    return K.mean(K.equal(K.round(y_true), K.round(y_pred)))

# --- Function to Save Plots ---
def save_figures(fig, filename):
    FIGURE_DIR = os.path.abspath(os.path.join(os.getcwd(), 'OriginalResult'))
    os.makedirs(FIGURE_DIR, exist_ok=True) # Create directory if it doesn't exist
    fig.savefig(os.path.join(FIGURE_DIR, filename + '.pdf'), bbox_inches='tight')
    print(f"Saved plot: {filename}.pdf")

# --- Plotting function for Training vs. Validation Loss ---
def plot_loss_curve(history):
    history_dict = history.history
    loss_values = history_dict['loss']
    val_loss_values = history_dict['val_loss']
    
    plt.figure(figsize=(10, 6))
    plt.plot(loss_values, 'b--', label='Training Loss')
    plt.plot(val_loss_values, 'r-', label='Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss (MSE)')
    plt.title('Model Training & Validation Loss')
    plt.legend()
    save_figures(plt, 'loss_curve')
    plt.close()

# --- Plotting function for Actual vs. Predicted values ---
def plot_actual_vs_prediction(y_test, y_test_pred):
    outcome = pd.DataFrame({'Actual': y_test, 'Predicted': y_test_pred.flatten()})
    df_sorted = outcome.head(40).sort_values(by="Actual")

    df_sorted.plot(kind='bar', figsize=(15, 8))
    plt.grid(which='major', linestyle='-', linewidth='0.5', color='green')
    plt.xlabel('Test Cases (Sample of 40)')
    plt.ylabel('Priority Values')
    plt.title("Comparison between 'Actual' and 'Predicted' Values")
    save_figures(plt, 'actual_vs_prediction_bar')
    plt.close()

# --- Plotting function for the Regression Line ---
def plot_regression_line(y_test, y_test_pred):
    plt.figure(figsize=(8, 8))
    plt.scatter(y_test, y_test_pred, alpha=0.5)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'k--', lw=3)
    plt.xlabel('Actual Priority Values')
    plt.ylabel('Predicted Priority Values')
    plt.title("Regression Plot: Actual vs. Predicted")
    save_figures(plt, 'regression_line')
    plt.close()

# --- NEW: Function to Calculate APFDc (Cost-aware APFD) ---
def calculate_apfdc(df_sorted, cost_column='Duration'):
    """
    Calculate APFDc considering test execution cost (duration).
    
    APFDc = (Sum of cost to detect each fault) / (total_cost * num_faults)
    """
    faults = df_sorted[df_sorted['Verdict'] == 1].copy()
    m = len(faults)  # Number of faults
    
    if m == 0:
        return 1.0  # Perfect score if no faults
    
    total_cost = df_sorted[cost_column].sum()
    
    # Calculate cumulative cost at each fault detection
    df_sorted['cumulative_cost'] = df_sorted[cost_column].cumsum()
    faults_with_cost = df_sorted[df_sorted['Verdict'] == 1].copy()
    
    sum_cost_to_faults = faults_with_cost['cumulative_cost'].sum()
    
    # APFDc formula
    apfdc = 1 - (sum_cost_to_faults / (total_cost * m)) + (1 / (2 * len(df_sorted)))
    
    return apfdc

# --- NEW: Function to Calculate TTFF (Time To First Failure) ---
def calculate_ttff(df_sorted, cost_column='Duration'):
    """
    Calculate Time To First Failure - cumulative cost until first fault is detected.
    Returns None if no faults exist.
    """
    first_fault_idx = df_sorted[df_sorted['Verdict'] == 1].first_valid_index()
    
    if first_fault_idx is None:
        return None  # No faults in this dataset
    
    # Get the position of first fault in sorted dataframe
    position = df_sorted.index.get_loc(first_fault_idx)
    
    # Calculate cumulative cost up to and including the first fault
    ttff = df_sorted.iloc[:position + 1][cost_column].sum()
    
    return ttff

# --- NEW: Function to Calculate Recall at K ---
def calculate_recall_at_k(df_sorted, k_percent=10):
    """
    Calculate recall: proportion of faults detected in top-k% of prioritized tests.
    
    Args:
        df_sorted: DataFrame sorted by predicted priority
        k_percent: Percentage of top tests to consider (default: 10%)
    
    Returns:
        recall: Proportion of faults found in top-k%
        k_count: Number of tests in top-k%
    """
    total_faults = (df_sorted['Verdict'] == 1).sum()
    
    if total_faults == 0:
        return 1.0, 0  # Perfect recall if no faults exist
    
    k_count = max(1, int(len(df_sorted) * k_percent / 100))
    top_k = df_sorted.head(k_count)
    faults_in_top_k = (top_k['Verdict'] == 1).sum()
    
    recall = faults_in_top_k / total_faults
    
    return recall, k_count


# ## 3. Data Loading and Preparation

# --- Load Dataset ---
df = pd.read_csv('CompEvol@beast2_deeporder_fixed_processed.csv') # Adjust path as needed
print("Dataset loaded successfully. Shape:", df.shape)

# --- Define Features (X) and Target (Y) ---
features = ['Duration', 'E1', 'E2', 'E3', 'LastRunFeature', 'DIST', 'CHANGE_IN_STATUS']
X = df[features]
Y = df['PRIORITY_VALUE']

# --- Split and Scale Data (Original: No random_state) ---
X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2)

scaler = MinMaxScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)


# ## 4. Build and Train the Neural Network

# --- Define the Model Architecture (Original) ---
# Use Lambda layers with mish activation to avoid JIT compilation
try:
    # Create mish as a simple lambda function
    mish_activation = lambda x: x * tf.nn.tanh(tf.nn.softplus(x))
    
    model = Sequential([
        Dense(10, input_shape=(len(features),)),
        Lambda(mish_activation),
        Dense(20),
        Lambda(mish_activation),
        Dense(15),
        Lambda(mish_activation),
        Dense(1) # Output layer for regression
    ])
    print("✅ Model built with custom Mish activation (using Lambda layers)")
except Exception as e:
    print(f"⚠️  Custom activation failed: {e}")
    print("   Using standard 'relu' activation as fallback")
    model = Sequential([
        Dense(10, input_shape=(len(features),), activation='relu'),
        Dense(20, activation='relu'),
        Dense(15, activation='relu'),
        Dense(1)
    ])

model.summary()

# --- Compile the Model ---
model.compile(optimizer=Adam(learning_rate=0.001), 
              loss='mean_squared_error', 
              metrics=[soft_acc],
              run_eagerly=False,  # Disable eager mode - may help with CPU-only
              jit_compile=False)  # Explicitly disable JIT compilation

# --- Train the Model (Original Parameters) ---
print("\nStarting model training with original parameters...")
information = model.fit(
    X_train_scaled, y_train,
    validation_split = 0.2, # Original method for validation
    epochs = 2,             # Original number of epochs
    shuffle = True,
    verbose = 1
)
print("Model training complete.")

# ## 5. Evaluate Model Performance

# --- Make Predictions ---
y_pred = model.predict(X_test_scaled)

# --- Calculate Metrics ---
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("\n--- Model Evaluation Metrics ---")
print(f"Mean Squared Error (MSE): {mse:.6f}")
print(f"R-squared (R2) Score:   {r2:.6f}")
print("--------------------------------\n")

# --- Generate and Save Plots ---
print("Generating and saving performance plots...")
plot_loss_curve(information) # Use 'information' history object
plot_actual_vs_prediction(y_test, y_pred)
plot_regression_line(y_test, y_pred)


# ## 6. Calculate Overall Metrics (APFD, APFDc, TTFF, Recall)

print("Calculating overall prioritization metrics...")
# --- Use the trained model to predict priorities for the entire dataset ---
X_full_scaled = scaler.transform(df[features])
df['CalcPrio'] = model.predict(X_full_scaled)

# --- Sort the dataframe by the new predicted priority ---
final_df = df.sort_values(by=['CalcPrio'], ascending=False).reset_index(drop=True)
final_df['ranking'] = final_df.index + 1

# --- Calculate APFD ---
faults = final_df[final_df['Verdict'] == 1]
m = len(faults) # Total number of failing tests
n = len(final_df) # Total number of tests

if m > 0:
    sum_of_ranks = faults['ranking'].sum()
    apfd = 1 - (sum_of_ranks / (m * n)) + (1 / (2 * n))
else:
    apfd = 1.0 # Perfect score if no faults exist

# --- NEW: Calculate APFDc ---
apfdc = calculate_apfdc(final_df, cost_column='Duration')

# --- NEW: Calculate TTFF ---
ttff = calculate_ttff(final_df, cost_column='Duration')

# --- NEW: Calculate Recall at different K values ---
recall_10, k_10 = calculate_recall_at_k(final_df, k_percent=10)
recall_20, k_20 = calculate_recall_at_k(final_df, k_percent=20)
recall_30, k_30 = calculate_recall_at_k(final_df, k_percent=30)

print(f"\n{'='*60}")
print(f"{'OVERALL PRIORITIZATION PERFORMANCE':^60}")
print(f"{'='*60}")
print(f"Total Test Cases (n):                    {n:>10}")
print(f"Total Failed Tests (m):                  {m:>10}")
print(f"-" * 60)
print(f"APFD (Position-based):                   {apfd:>10.6f}")
print(f"APFDc (Cost-aware):                      {apfdc:>10.6f}")
print(f"TTFF (Time to First Failure):            {ttff:>10.2f} time units" if ttff else "TTFF: No failures detected")
print(f"-" * 60)
print(f"Recall@10% (top {k_10} tests):             {recall_10:>10.2%}")
print(f"Recall@20% (top {k_20} tests):             {recall_20:>10.2%}")
print(f"Recall@30% (top {k_30} tests):             {recall_30:>10.2%}")
print(f"{'='*60}\n")


# ## 7. Calculate Metrics per Cycle (NAPFD, NAPFDc, TTFF, Recall)

print("Calculating metrics per cycle...")
NAPFD_per_cycle = []
NAPFDc_per_cycle = []
TTFF_per_cycle = []
Recall10_per_cycle = []
Recall20_per_cycle = []

unique_cycles = sorted(df['Cycle'].unique())

for cycle in unique_cycles:
    df_cycle = df[df['Cycle'] == cycle].copy()
    
    if df_cycle.empty:
        continue
    
    # Scale features and predict priorities for this cycle
    X_cycle_scaled = scaler.transform(df_cycle[features])
    df_cycle['CalcPrio'] = model.predict(X_cycle_scaled)
    
    # Sort by priority
    final_df_cycle = df_cycle.sort_values(by=['CalcPrio'], ascending=False).reset_index(drop=True)
    final_df_cycle['ranking'] = final_df_cycle.index + 1
    
    # Calculate NAPFD for the cycle
    cycle_faults = final_df_cycle[final_df_cycle['Verdict'] == 1]
    m_cycle = len(cycle_faults)
    n_cycle = len(final_df_cycle)
    
    if m_cycle > 0:
        sum_of_ranks_cycle = cycle_faults['ranking'].sum()
        napfd = 1 - (sum_of_ranks_cycle / (m_cycle * n_cycle)) + (1 / (2 * n_cycle))
        NAPFD_per_cycle.append(napfd)
    else:
        NAPFD_per_cycle.append(1.0) # Perfect score if no faults in cycle
    
    # NEW: Calculate NAPFDc for the cycle
    napfdc = calculate_apfdc(final_df_cycle, cost_column='Duration')
    NAPFDc_per_cycle.append(napfdc)
    
    # NEW: Calculate TTFF for the cycle
    ttff_cycle = calculate_ttff(final_df_cycle, cost_column='Duration')
    TTFF_per_cycle.append(ttff_cycle if ttff_cycle is not None else 0)
    
    # NEW: Calculate Recall for the cycle
    recall10_cycle, _ = calculate_recall_at_k(final_df_cycle, k_percent=10)
    recall20_cycle, _ = calculate_recall_at_k(final_df_cycle, k_percent=20)
    Recall10_per_cycle.append(recall10_cycle)
    Recall20_per_cycle.append(recall20_cycle)

avg_napfd = mean(NAPFD_per_cycle) if NAPFD_per_cycle else 0
avg_napfdc = mean(NAPFDc_per_cycle) if NAPFDc_per_cycle else 0
avg_ttff = mean([t for t in TTFF_per_cycle if t > 0]) if any(t > 0 for t in TTFF_per_cycle) else 0
avg_recall10 = mean(Recall10_per_cycle) if Recall10_per_cycle else 0
avg_recall20 = mean(Recall20_per_cycle) if Recall20_per_cycle else 0

print(f"\n{'='*60}")
print(f"{'AVERAGE METRICS PER CYCLE':^60}")
print(f"{'='*60}")
print(f"Avg NAPFD per Cycle:                     {avg_napfd:>10.6f}")
print(f"Avg NAPFDc per Cycle:                    {avg_napfdc:>10.6f}")
print(f"Avg TTFF per Cycle:                      {avg_ttff:>10.2f} time units")
print(f"Avg Recall@10% per Cycle:                {avg_recall10:>10.2%}")
print(f"Avg Recall@20% per Cycle:                {avg_recall20:>10.2%}")
print(f"{'='*60}\n")

# --- Plot NAPFD Over Cycles ---
plt.figure(figsize=(15, 8))
plt.plot(unique_cycles, NAPFD_per_cycle, color='red', marker='o', linestyle='-', label='NAPFD')
plt.plot(unique_cycles, NAPFDc_per_cycle, color='blue', marker='s', linestyle='--', label='NAPFDc')
plt.title('NAPFD & NAPFDc Fluctuation Over CI Cycles', fontsize=16)
plt.xlabel('CI Cycle', fontsize=14)
plt.ylabel('Normalized APFD', fontsize=14)
plt.ylim(0, 1.05)
plt.legend()
plt.grid(True)
save_figures(plt, 'NAPFD_NAPFDc_per_cycle')
plt.close()

# --- NEW: Plot TTFF Over Cycles ---
plt.figure(figsize=(15, 8))
plt.plot(unique_cycles, TTFF_per_cycle, color='green', marker='D', linestyle='-')
plt.title('TTFF (Time to First Failure) Over CI Cycles', fontsize=16)
plt.xlabel('CI Cycle', fontsize=14)
plt.ylabel('TTFF (Time Units)', fontsize=14)
plt.grid(True)
save_figures(plt, 'TTFF_per_cycle')
plt.close()

# --- NEW: Plot Recall Over Cycles ---
plt.figure(figsize=(15, 8))
plt.plot(unique_cycles, Recall10_per_cycle, color='purple', marker='o', linestyle='-', label='Recall@10%')
plt.plot(unique_cycles, Recall20_per_cycle, color='orange', marker='s', linestyle='--', label='Recall@20%')
plt.title('Recall Fluctuation Over CI Cycles', fontsize=16)
plt.xlabel('CI Cycle', fontsize=14)
plt.ylabel('Recall', fontsize=14)
plt.ylim(0, 1.05)
plt.legend()
plt.grid(True)
save_figures(plt, 'Recall_per_cycle')
plt.close()


# ## 8. Final Timings and Summary

total_time = datetime.now() - startTime
print("\n--- Execution Summary ---")
print(f"Total Execution Time: {total_time}")
print("Analysis complete. All plots saved to the 'OriginalResult' folder.")
print("-------------------------\n")

# --- Store final metrics in a DataFrame for a clean summary ---
summary_data = {
    'Metric': [
        'MSE', 
        'R2 Score', 
        'Overall APFD', 
        'Overall APFDc',
        'Overall TTFF',
        'Overall Recall@10%',
        'Overall Recall@20%',
        'Overall Recall@30%',
        'Avg NAPFD per Cycle',
        'Avg NAPFDc per Cycle',
        'Avg TTFF per Cycle',
        'Avg Recall@10% per Cycle',
        'Avg Recall@20% per Cycle'
    ],
    'Value': [
        f'{mse:.6f}',
        f'{r2:.6f}',
        f'{apfd:.6f}',
        f'{apfdc:.6f}',
        f'{ttff:.2f}' if ttff else 'N/A',
        f'{recall_10:.2%}',
        f'{recall_20:.2%}',
        f'{recall_30:.2%}',
        f'{avg_napfd:.6f}',
        f'{avg_napfdc:.6f}',
        f'{avg_ttff:.2f}',
        f'{avg_recall10:.2%}',
        f'{avg_recall20:.2%}'
    ]
}
summary_df = pd.DataFrame(summary_data)
print("\n" + "="*60)
print("FINAL METRICS SUMMARY".center(60))
print("="*60)
print(summary_df.to_string(index=False))
print("="*60)

# --- Save summary to CSV ---
summary_df.to_csv(os.path.join('OriginalResult', 'metrics_summary.csv'), index=False)
print(f"\n✅ Metrics summary saved to 'OriginalResult/metrics_summary.csv'")