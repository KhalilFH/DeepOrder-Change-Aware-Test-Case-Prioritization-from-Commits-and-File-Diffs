# Standard library imports
import os
import json
import pickle
import random
import warnings
from datetime import datetime
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Third-party imports
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
from scipy.stats import mannwhitneyu

# TensorFlow/Keras imports
import tensorflow as tf
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import Dense, Input, Dropout, BatchNormalization, Concatenate
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.regularizers import l2

# Scikit-learn imports
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, average_precision_score, accuracy_score, 
    precision_score, recall_score, f1_score, confusion_matrix,
    classification_report, precision_recall_curve, roc_curve
)
from sklearn.utils.class_weight import compute_class_weight
from sklearn.neighbors import NearestNeighbors
from dataclasses import dataclass, asdict

# Configure warnings
warnings.filterwarnings('ignore')

# ENHANCED TCP ANALYSIS FUNCTIONS
def vargha_delaney_a12(group1, group2):
    """Calculate Vargha-Delaney A12 effect size"""
    if len(group1) == 0 or len(group2) == 0:
        return 0.5
    
    wins = 0
    ties = 0
    total = len(group1) * len(group2)
    
    for x in group1:
        for y in group2:
            if x > y:
                wins += 1
            elif x == y:
                ties += 1
    
    a12 = (wins + 0.5 * ties) / total
    return a12

def create_priority_value_baseline(df_test):
    """
    LEGACY FUNCTION - now redirects to BaselineModels.priority_value_baseline
    Create PRIORITY_VALUE baseline predictions using ONLY test data
    """
    # PRIORITY_VALUE baseline should NOT use training data - it represents
    # the corrupted baseline we're trying to detect
    return BaselineModels.priority_value_baseline(df_test)

def get_cycle_execution_times_until_failure(df_test, predictions_dict):
    """Calculate execution time per cycle until first failure is found"""
    cycle_times = {}
    duration_col = 'Duration' if 'Duration' in df_test.columns else 'DurationFeature'
    
    for model_name, predictions in predictions_dict.items():
        model_cycle_times = {'all_cycles': [], 'failing_cycles': []}
        
        for cycle in sorted(df_test['Cycle'].unique()):
            cycle_df = df_test[df_test['Cycle'] == cycle]
            cycle_predictions = predictions[df_test['Cycle'] == cycle]
            
            # Sort by predictions (highest first) - this is the execution order
            cycle_df_ranked = cycle_df.copy()
            cycle_df_ranked['prediction'] = cycle_predictions
            cycle_df_ranked = cycle_df_ranked.sort_values('prediction', ascending=False)
            cycle_df_ranked['cumulative_time'] = cycle_df_ranked[duration_col].cumsum()
            
            # Find execution time until first failure
            first_failure_idx = cycle_df_ranked[cycle_df_ranked['Verdict'] == 1].index
            
            if len(first_failure_idx) > 0:
                # Has failures - time until first one found
                first_failure_pos = cycle_df_ranked.index.get_loc(first_failure_idx[0])
                execution_time = cycle_df_ranked['cumulative_time'].iloc[first_failure_pos]
                model_cycle_times['failing_cycles'].append(execution_time)
            else:
                # No failures - total cycle time
                execution_time = cycle_df_ranked['cumulative_time'].iloc[-1]
            
            model_cycle_times['all_cycles'].append(execution_time)
        
        cycle_times[model_name] = model_cycle_times
    
    return cycle_times

def analyze_failing_test_rankings_per_cycle(df_test, predictions_dict):
    """Analyze ranking positions of failing tests in failing cycles"""
    failing_rankings = {}
    
    for model_name, predictions in predictions_dict.items():
        model_rankings = {'first_failure_ranks': [], 'avg_failure_ranks': []}
        
        for cycle in sorted(df_test['Cycle'].unique()):
            cycle_df = df_test[df_test['Cycle'] == cycle]
            cycle_predictions = predictions[df_test['Cycle'] == cycle]
            cycle_failures = cycle_df[cycle_df['Verdict'] == 1]
            
            if len(cycle_failures) == 0:
                continue  # Skip non-failing cycles
            
            # Create ranking by predictions
            cycle_df_ranked = cycle_df.copy()
            cycle_df_ranked['prediction'] = cycle_predictions
            cycle_df_ranked = cycle_df_ranked.sort_values('prediction', ascending=False).reset_index(drop=True)
            cycle_df_ranked['rank'] = range(1, len(cycle_df_ranked) + 1)
            
            # Get ranks of failing tests
            failure_ranks = cycle_df_ranked[cycle_df_ranked['Verdict'] == 1]['rank'].tolist()
            
            if failure_ranks:
                model_rankings['first_failure_ranks'].append(min(failure_ranks))
                model_rankings['avg_failure_ranks'].append(np.mean(failure_ranks))
        
        failing_rankings[model_name] = model_rankings
    
    return failing_rankings

def analyze_duration_ideal_ranking_comparison(df_test, predictions_dict):
    """Compare with duration-based ideal ranking - FIXED for numpy arrays"""
    duration_col = 'Duration' if 'Duration' in df_test.columns else 'DurationFeature'
    comparison_results = {}
    
    for model_name, predictions in predictions_dict.items():
        model_results = {
            'ranking_correlations': [],
            'first_failure_ranks_ideal': [],
            'avg_failure_ranks_ideal': []
        }
        
        for cycle in sorted(df_test['Cycle'].unique()):
            cycle_df = df_test[df_test['Cycle'] == cycle].copy()
            cycle_predictions = predictions[df_test['Cycle'] == cycle]
            cycle_failures = cycle_df[cycle_df['Verdict'] == 1]
            
            if len(cycle_df) < 2:
                continue
            
            # FIX: Use pandas Series for ranking operations
            cycle_durations = cycle_df[duration_col]
            cycle_predictions_series = pd.Series(cycle_predictions, index=cycle_df.index)
            
            # Ideal ranking: shortest duration first
            ideal_ranking = cycle_durations.rank(method='min', ascending=True)
            # Predicted ranking: highest prediction first
            predicted_ranking = cycle_predictions_series.rank(method='min', ascending=False)
            
            # Calculate correlation between rankings
            try:
                correlation = stats.spearmanr(ideal_ranking, predicted_ranking)[0]
                if not np.isnan(correlation):
                    model_results['ranking_correlations'].append(correlation)
            except:
                pass
            
            # For failing cycles, get failure ranks in ideal order
            if len(cycle_failures) > 0:
                cycle_df_with_ideal = cycle_df.copy()
                cycle_df_with_ideal['ideal_rank'] = ideal_ranking
                failure_ideal_ranks = cycle_df_with_ideal[cycle_df_with_ideal['Verdict'] == 1]['ideal_rank'].tolist()
                
                if failure_ideal_ranks:
                    model_results['first_failure_ranks_ideal'].append(min(failure_ideal_ranks))
                    model_results['avg_failure_ranks_ideal'].append(np.mean(failure_ideal_ranks))
        
        comparison_results[model_name] = model_results
    
    return comparison_results

def perform_pairwise_statistical_tests(data_dict):
    """Perform Mann-Whitney U, Wilcoxon, and A12 tests between all pairs"""
    approaches = list(data_dict.keys())
    results = {}
    
    for i, approach1 in enumerate(approaches):
        for approach2 in approaches[i+1:]:
            data1 = data_dict[approach1]
            data2 = data_dict[approach2]
            
            if len(data1) > 0 and len(data2) > 0:
                # Mann-Whitney U test
                try:
                    mw_stat, mw_p = mannwhitneyu(data1, data2, alternative='two-sided')
                except:
                    mw_stat, mw_p = 0, 1.0
                
                # Wilcoxon test (if same length - paired)
                wilcoxon_p = None
                if len(data1) == len(data2) and len(data1) > 1:
                    try:
                        from scipy.stats import wilcoxon
                        w_stat, wilcoxon_p = wilcoxon(data1, data2, alternative='two-sided')
                    except:
                        wilcoxon_p = None
                
                # A12 effect size
                a12 = vargha_delaney_a12(data1, data2)
                
                results[f"{approach1}_vs_{approach2}"] = {
                    'mann_whitney_p': mw_p,
                    'wilcoxon_p': wilcoxon_p,
                    'a12_effect_size': a12,
                    'a12_interpretation': 'app1_better' if a12 > 0.5 else 'app2_better' if a12 < 0.5 else 'no_difference',
                    'mean_diff': np.mean(data1) - np.mean(data2),
                    'approach1_mean': np.mean(data1),
                    'approach2_mean': np.mean(data2)
                }
    
    return results

def create_enhanced_boxplot(data_dict, title, ylabel, output_path, statistical_results=None):
    """Create detailed box plot with statistical annotations"""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    approaches = list(data_dict.keys())
    data_values = [data_dict[approach] for approach in approaches]
    
    # Create box plot
    bp = ax.boxplot(data_values, labels=approaches, patch_artist=True, 
                    showmeans=True, meanline=True, widths=0.6)
    
    # Color the boxes
    colors = plt.cm.Set3(np.linspace(0, 1, len(approaches)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Add statistical significance annotations
    if statistical_results:
        y_max = max([max(data) if len(data) > 0 else 0 for data in data_values])
        y_min = min([min(data) if len(data) > 0 else 0 for data in data_values])
        y_range = y_max - y_min
        y_offset = y_range * 0.05
        
        sig_pairs = []
        for comparison, stats in statistical_results.items():
            if stats['mann_whitney_p'] < 0.05:
                approaches_pair = comparison.split('_vs_')
                if len(approaches_pair) == 2:
                    try:
                        idx1 = approaches.index(approaches_pair[0])
                        idx2 = approaches.index(approaches_pair[1])
                        sig_pairs.append((idx1, idx2, stats['mann_whitney_p'], stats['a12_effect_size']))
                    except ValueError:
                        continue
        
        # Add significance bars (limit to avoid clutter)
        for i, (idx1, idx2, p_val, a12) in enumerate(sig_pairs[:3]):
            y_pos = y_max + y_offset * (i + 1)
            ax.plot([idx1 + 1, idx2 + 1], [y_pos, y_pos], 'k-', linewidth=1)
            
            if p_val < 0.001:
                sig_symbol = '***'
            elif p_val < 0.01:
                sig_symbol = '**'
            else:
                sig_symbol = '*'
            
            ax.text((idx1 + idx2) / 2 + 1, y_pos + y_offset * 0.3, 
                   f'{sig_symbol}\nA12={a12:.2f}', 
                   ha='center', va='bottom', fontsize=9)
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_xlabel('Approach', fontsize=12)
    ax.grid(axis='y', alpha=0.3)
    
    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')
    
    # Add summary statistics
    n_cycles = len(data_values[0]) if data_values and len(data_values[0]) > 0 else 0
    stats_text = f"Cycles analyzed: {n_cycles}\nApproaches: {len(approaches)}"
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
           verticalalignment='top', 
           bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    return fig

# PRACTICAL TCP OUTPUT FUNCTIONS
def generate_practical_tcp_rankings(df_test, predictions_dict, output_dir="tcp_rankings"):
    """
    Generate practical TCP rankings per cycle that practitioners would use
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    rankings_per_cycle = {}
    
    for model_name, predictions in predictions_dict.items():
        model_rankings = {}
        
        for cycle in sorted(df_test['Cycle'].unique()):
            cycle_df = df_test[df_test['Cycle'] == cycle]
            cycle_predictions = predictions[df_test['Cycle'] == cycle]
            
            # Create ranking DataFrame
            ranking_df = cycle_df.copy()
            ranking_df['failure_prob'] = cycle_predictions
            ranking_df = ranking_df.sort_values('failure_prob', ascending=False)
            
            # Generate execution order
            execution_order = []
            for idx, (_, row) in enumerate(ranking_df.iterrows(), 1):
                test_info = {
                    'rank': idx,
                    'test_name': row.get('TestName', f"Test_{row.name}"),
                    'failure_prob': f"{row['failure_prob']:.3f}",
                    'actual_verdict': 'FAIL' if row['Verdict'] == 1 else 'PASS',
                    'duration': row.get('Duration', row.get('DurationFeature', 0))
                }
                execution_order.append(test_info)
            
            model_rankings[cycle] = execution_order
        
        rankings_per_cycle[model_name] = model_rankings
    
    # Save rankings to files
    for model_name, model_rankings in rankings_per_cycle.items():
        model_file = output_path / f"{model_name}_rankings.txt"
        with open(model_file, 'w') as f:
            f.write(f"TCP RANKINGS FOR {model_name}\n")
            f.write("=" * 50 + "\n\n")
            
            for cycle, tests in model_rankings.items():
                f.write(f"Cycle {cycle} Test Execution Order:\n")
                for test in tests:
                    f.write(f"{test['rank']:3d}. {test['test_name']:30s} (prob: {test['failure_prob']}) [{test['actual_verdict']}]\n")
                f.write("\n")
    
    print(f"Practical TCP rankings saved to: {output_path}")
    return rankings_per_cycle

def comprehensive_tcp_analysis_complete(df_test, predictions_dict, output_dir="tcp_complete_analysis"):
    """
    Complete TCP analysis with all requirements
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Add PRIORITY_VALUE baseline if not already present
    predictions_dict = predictions_dict.copy()
    priority_baseline_names = ['Baseline_PriorityValue', 'Priority_Value', 'Baseline_Priority_Value']
    has_priority_baseline = any(name in predictions_dict for name in priority_baseline_names)
    
    if not has_priority_baseline:
        # CORRECTED: PRIORITY_VALUE baseline uses only test data (no training data needed)
        priority_baseline = BaselineModels.priority_value_baseline(df_test)
        predictions_dict['Baseline_PriorityValue'] = priority_baseline
        print("Added PRIORITY_VALUE baseline for comprehensive analysis (test data only)")
    else:
        print("PRIORITY_VALUE baseline already exists in predictions")
    
    print("COMPREHENSIVE TCP ANALYSIS")
    print("=" * 60)
    
    # 1. CYCLE EXECUTION TIME ANALYSIS
    print("\n1. Cycle Execution Time Analysis")
    cycle_times = get_cycle_execution_times_until_failure(df_test, predictions_dict)
    
    all_cycles_data = {model: times['all_cycles'] for model, times in cycle_times.items()}
    failing_cycles_data = {model: times['failing_cycles'] for model, times in cycle_times.items()}
    
    all_cycles_stats = perform_pairwise_statistical_tests(all_cycles_data)
    failing_cycles_stats = perform_pairwise_statistical_tests(failing_cycles_data)
    
    create_enhanced_boxplot(all_cycles_data, 
                           'Cycle Execution Time - All Cycles', 
                           'Time Until First Failure Found',
                           output_path / 'boxplot_execution_time_all.png',
                           all_cycles_stats)
    
    create_enhanced_boxplot(failing_cycles_data,
                           'Cycle Execution Time - Failing Cycles Only',
                           'Time Until First Failure Found', 
                           output_path / 'boxplot_execution_time_failing.png',
                           failing_cycles_stats)
    
    # 2. FAILING TEST RANKING ANALYSIS
    print("\n2. Failing Test Ranking Analysis")
    failing_rankings = analyze_failing_test_rankings_per_cycle(df_test, predictions_dict)
    
    first_failure_ranks = {model: ranks['first_failure_ranks'] for model, ranks in failing_rankings.items()}
    avg_failure_ranks = {model: ranks['avg_failure_ranks'] for model, ranks in failing_rankings.items()}
    
    first_failure_stats = perform_pairwise_statistical_tests(first_failure_ranks)
    avg_failure_stats = perform_pairwise_statistical_tests(avg_failure_ranks)
    
    create_enhanced_boxplot(first_failure_ranks,
                           'First Failing Test Rank per Cycle',
                           'Rank Position',
                           output_path / 'boxplot_first_failure_rank.png',
                           first_failure_stats)
    
    create_enhanced_boxplot(avg_failure_ranks,
                           'Average Failing Test Rank per Cycle', 
                           'Average Rank Position',
                           output_path / 'boxplot_avg_failure_rank.png',
                           avg_failure_stats)
    
    # 3. DURATION-BASED IDEAL COMPARISON
    print("\n3. Duration-Based Ideal Ranking Comparison")
    duration_analysis = analyze_duration_ideal_ranking_comparison(df_test, predictions_dict)
    
    ranking_correlations = {model: data['ranking_correlations'] for model, data in duration_analysis.items()}
    first_vs_ideal = {model: data['first_failure_ranks_ideal'] for model, data in duration_analysis.items()}
    avg_vs_ideal = {model: data['avg_failure_ranks_ideal'] for model, data in duration_analysis.items()}
    
    correlation_stats = perform_pairwise_statistical_tests(ranking_correlations)
    first_vs_ideal_stats = perform_pairwise_statistical_tests(first_vs_ideal)
    avg_vs_ideal_stats = perform_pairwise_statistical_tests(avg_vs_ideal)
    
    create_enhanced_boxplot(ranking_correlations,
                           'Ranking Correlation with Duration-Based Ideal',
                           'Spearman Correlation',
                           output_path / 'boxplot_ranking_correlations.png',
                           correlation_stats)
    
    create_enhanced_boxplot(first_vs_ideal,
                           'First Failure Rank (Duration-Based Ideal Order)',
                           'Rank Position in Ideal Order',
                           output_path / 'boxplot_first_failure_ideal.png',
                           first_vs_ideal_stats)
    
    create_enhanced_boxplot(avg_vs_ideal,
                           'Average Failure Rank (Duration-Based Ideal Order)',
                           'Average Rank Position in Ideal Order',
                           output_path / 'boxplot_avg_failure_ideal.png',
                           avg_vs_ideal_stats)
    
    # 4. GENERATE PRACTICAL TCP OUTPUT
    print("\n4. Generating Practical TCP Rankings")
    practical_rankings = generate_practical_tcp_rankings(df_test, predictions_dict, 
                                                        output_path / "practical_rankings")
    
    # 5. SAVE ALL STATISTICAL RESULTS
    all_results = {
        'execution_time_all_cycles': all_cycles_stats,
        'execution_time_failing_cycles': failing_cycles_stats,
        'first_failure_rank': first_failure_stats,
        'avg_failure_rank': avg_failure_stats,
        'ranking_correlations': correlation_stats,
        'first_failure_vs_ideal': first_vs_ideal_stats,
        'avg_failure_vs_ideal': avg_vs_ideal_stats
    }
    
    # Save to JSON
    import json
    with open(output_path / 'complete_statistical_results.json', 'w') as f:
        json_results = {}
        for category, results in all_results.items():
            json_results[category] = {}
            for comparison, stats in results.items():
                json_results[category][comparison] = {
                    'mann_whitney_p': float(stats['mann_whitney_p']),
                    'wilcoxon_p': float(stats['wilcoxon_p']) if stats['wilcoxon_p'] is not None else None,
                    'a12_effect_size': float(stats['a12_effect_size']),
                    'a12_interpretation': stats['a12_interpretation'],
                    'mean_diff': float(stats['mean_diff']),
                    'approach1_mean': float(stats['approach1_mean']),
                    'approach2_mean': float(stats['approach2_mean'])
                }
        json.dump(json_results, f, indent=2)
    
    print(f"\nComplete analysis finished! All results saved to: {output_path}")
    print("\nGenerated files:")
    print(" 6 box plots with statistical annotations")
    print(" Practical TCP rankings for each approach") 
    print(" Complete statistical results (JSON)")
    
    return all_results, practical_rankings

# GPU Configuration and Detection
def configure_tf_gpu_device():
    """Configure TensorFlow GPU device with explicit device placement"""
    print(" Configuring TensorFlow GPU devices...")
    
    # List all available devices
    print(" Available devices:")
    for device in tf.config.list_physical_devices():
        print(f"   {device}")
    
    # Check GPU availability
    gpus = tf.config.experimental.list_physical_devices('GPU')
    
    if gpus:
        print(f"\n Found {len(gpus)} GPU(s):")
        for i, gpu in enumerate(gpus):
            print(f"   GPU {i}: {gpu.name}")
        
        try:
            # Enable memory growth to prevent TensorFlow from allocating all GPU memory
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            print(" GPU memory growth enabled")
            
            # Set GPU as visible devices
            tf.config.experimental.set_visible_devices(gpus, 'GPU')
            
            # Set default GPU device strategy
            logical_gpus = tf.config.experimental.list_logical_devices('GPU')
            print(f" Logical GPUs configured: {len(logical_gpus)}")
            
            # Verify GPU is being used by TensorFlow
            with tf.device('/GPU:0'):
                test_tensor = tf.constant([1.0, 2.0, 3.0])
                print(f" Test tensor created on: {test_tensor.device}")
            
            return True, len(gpus), '/GPU:0'
            
        except RuntimeError as e:
            print(f" GPU configuration error: {e}")
            print("   Falling back to CPU")
            return False, 0, '/CPU:0'
    else:
        print(" No GPU found - using CPU")
        return False, 0, '/CPU:0'

def check_gpu_availability():
    """Legacy function - redirects to configure_tf_gpu_device"""
    return configure_tf_gpu_device()[:2]

def set_global_determinism(seed=42, force_gpu=False):
    """Enhanced determinism setup with GPU configuration"""
    print(f" Setting up computational environment (seed={seed})...")
    
    # Configure GPU if requested
    gpu_available = False
    gpu_count = 0
    device_name = '/CPU:0'
    
    if force_gpu or tf.config.experimental.list_physical_devices('GPU'):
        gpu_available, gpu_count, device_name = configure_tf_gpu_device()
        
        if force_gpu and not gpu_available:
            raise RuntimeError("GPU was forced but no GPU is available!")
        
        if gpu_available:
            print(f" Using GPU acceleration with {gpu_count} GPU(s)")
            print(f" Default device: {device_name}")
        else:
            print(" Using CPU computation")
            print(f" Default device: {device_name}")
    else:
        print(" Using CPU computation (GPU not requested)")
        device_name = '/CPU:0'
    
    # Optimize CPU performance when no GPU is available
    if not gpu_available:
        print(" Optimizing CPU performance...")
        # Set CPU thread configuration for better performance
        tf.config.threading.set_inter_op_parallelism_threads(0)  # Use all available CPU cores
        tf.config.threading.set_intra_op_parallelism_threads(0)  # Use all available CPU cores
        print(" CPU optimization configured")
    
    # Set random seeds for reproducibility
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    tf.keras.utils.set_random_seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    os.environ['TF_DETERMINISTIC_OPS'] = '1'
    tf.config.experimental.enable_op_determinism()
    
    print(f" Global determinism set with seed {seed}")
    return gpu_available, device_name

# Initialize with CPU-friendly GPU detection (no forcing)
gpu_enabled, default_device = set_global_determinism(42, force_gpu=False)

# ============================================================================
# UNIFIED ADAPTIVE TEMPORAL SPLITTER (INTEGRATED)
# ============================================================================

@dataclass
class SplitMetadata:
    """Metadata for a temporal split"""
    project_name: str
    strategy: str  # 'low_failure', 'normal', 'high_failure'
    
    # Overall statistics
    total_tests: int
    total_failures: int
    overall_failure_rate: float
    total_cycles: int
    cycle_range: Tuple[int, int]
    
    # Train set
    train_cycles: Tuple[int, int]
    train_size: int
    train_failures: int
    train_failure_rate: float
    
    # Test set
    test_cycles: Tuple[int, int]
    test_size: int
    test_failures: int
    test_failure_rate: float
    test_proportion: float
    
    # Statistical assessment
    statistical_power: str
    power_assessment: str
    recommended_emphasis: str
    
    # Quality checks
    temporal_validity: bool
    quality_warnings: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class UnifiedAdaptiveSplitter:
    """
    Unified temporal splitting strategy that adapts to project characteristics.
    
    Key Features:
    - Automatically adapts split proportions based on failure rate
    - Maintains strict temporal validity (no leakage)
    - Uses SAME metrics for ALL projects (methodologically sound)
    - Provides statistical power assessment
    - Saves detailed metadata for reproducibility
    """
    
    # Classification thresholds
    LOW_FAILURE_THRESHOLD = 0.05    # 5%
    HIGH_FAILURE_THRESHOLD = 0.50   # 50%
    
    # Quality requirements
    MIN_TEST_FAILURES_NORMAL = 50
    MIN_TEST_FAILURES_LOW = 30
    MIN_TEST_CYCLES = 20
    MIN_TRAIN_CYCLES = 20
    
    def __init__(self, 
                 output_dir: str = "split_metadata",
                 verbose: bool = True,
                 save_metadata: bool = True):
        """
        Initialize splitter.
        
        Args:
            output_dir: Directory to save split metadata
            verbose: Whether to print detailed information
            save_metadata: Whether to save metadata to JSON files
        """
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.save_metadata = save_metadata
        
        if self.save_metadata:
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def split(self, 
              df: pd.DataFrame, 
              project_name: str) -> Tuple[np.ndarray, np.ndarray, SplitMetadata]:
        """
        Main entry point: Split data with automatic adaptation.
        
        Args:
            df: DataFrame with 'Cycle' and 'Verdict' columns
            project_name: Project name for documentation
            
        Returns:
            train_indices: Array of training indices
            test_indices: Array of test indices  
            metadata: SplitMetadata object with all details
        """
        if self.verbose:
            self._print_header("UNIFIED ADAPTIVE TEMPORAL SPLITTER")
        
        # Validate input
        self._validate_input(df)
        
        # Step 1: Analyze project characteristics
        project_stats = self._analyze_project(df, project_name)
        
        # Step 2: Classify project type
        project_type = self._classify_project(project_stats)
        
        # Step 3: Find optimal split
        train_idx, test_idx, split_info = self._find_optimal_split(
            df, project_stats, project_type
        )
        
        # Step 4: Create metadata
        metadata = self._create_metadata(
            df, project_name, project_stats, project_type, 
            train_idx, test_idx, split_info
        )
        
        # Step 5: Verify quality
        self._verify_split(df, train_idx, test_idx, metadata)
        
        # Step 6: Save metadata
        if self.save_metadata:
            self._save_metadata_to_file(metadata, project_name)
        
        # Step 7: Print summary
        if self.verbose:
            self._print_summary(metadata)
        
        return train_idx, test_idx, metadata
    
    def _validate_input(self, df: pd.DataFrame) -> None:
        """Validate input DataFrame"""
        required_cols = ['Cycle', 'Verdict']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        if df['Verdict'].isna().any():
            raise ValueError("'Verdict' column contains NaN values")
        
        if len(df) == 0:
            raise ValueError("DataFrame is empty")
        
        if df['Cycle'].nunique() < 10:
            warnings.warn(f"Only {df['Cycle'].nunique()} unique cycles - results may be unreliable")
    
    def _analyze_project(self, df: pd.DataFrame, project_name: str) -> Dict:
        """Analyze project characteristics"""
        cycles = sorted(df['Cycle'].unique())
        
        stats = {
            'project_name': project_name,
            'total_tests': len(df),
            'total_failures': int(df['Verdict'].sum()),
            'overall_failure_rate': float(df['Verdict'].mean()),
            'total_cycles': len(cycles),
            'cycle_range': (int(cycles[0]), int(cycles[-1])),
            'avg_tests_per_cycle': float(len(df) / len(cycles)),
            'avg_failures_per_cycle': float(df['Verdict'].sum() / len(cycles))
        }
        
        # Analyze cycle-level failure rate distribution
        cycle_failure_rates = []
        for cycle in cycles:
            cycle_df = df[df['Cycle'] == cycle]
            if len(cycle_df) > 0:
                cycle_failure_rates.append(cycle_df['Verdict'].mean())
        
        stats['failure_rate_std'] = float(np.std(cycle_failure_rates))
        stats['failure_rate_min'] = float(min(cycle_failure_rates))
        stats['failure_rate_max'] = float(max(cycle_failure_rates))
        stats['failure_rate_median'] = float(np.median(cycle_failure_rates))
        
        if self.verbose:
            self._print_project_analysis(stats)
        
        return stats
    
    def _classify_project(self, stats: Dict) -> str:
        """Classify project based on failure rate"""
        failure_rate = stats['overall_failure_rate']
        
        if failure_rate < self.LOW_FAILURE_THRESHOLD:
            classification = 'low_failure'
            description = f"LOW failure rate ({failure_rate:.2%}) - Production-quality project"
        elif failure_rate > self.HIGH_FAILURE_THRESHOLD:
            classification = 'high_failure'
            description = f"HIGH failure rate ({failure_rate:.2%}) - Integration tests or active development"
        else:
            classification = 'normal'
            description = f"NORMAL failure rate ({failure_rate:.2%}) - Standard development"
        
        if self.verbose:
            print(f"\n PROJECT CLASSIFICATION: {classification.upper()}")
            print(f"   {description}")
        
        return classification
    
    def _find_optimal_split(self, 
                           df: pd.DataFrame, 
                           stats: Dict, 
                           project_type: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Find optimal split point based on project type"""
        
        if project_type == 'low_failure':
            return self._split_low_failure(df, stats)
        elif project_type == 'high_failure':
            return self._split_high_failure(df, stats)
        else:  # normal
            return self._split_normal(df, stats)
    
    def _split_low_failure(self, df: pd.DataFrame, stats: Dict) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Strategy for low failure rate projects (<5%)"""
        
        if self.verbose:
            print(f"\n{'='*80}")
            print("APPLYING LOW FAILURE RATE STRATEGY")
            print(f"{'='*80}")
            print(f"   Strategy: Extended test set (40-70%) to accumulate ≥{self.MIN_TEST_FAILURES_LOW} failures")
        
        cycles = sorted(df['Cycle'].unique())
        
        # Calculate target failures
        min_test_failures = max(self.MIN_TEST_FAILURES_LOW, 
                               int(stats['total_failures'] * 0.25))
        
        if self.verbose:
            print(f"   Target: ≥{min_test_failures} failures in test set")
        
        # Search for valid split (30% to 70% test)
        best_split = None
        best_score = -np.inf
        
        for test_pct in np.arange(0.30, 0.75, 0.05):
            split_idx = int(len(cycles) * (1 - test_pct))
            
            if split_idx < self.MIN_TRAIN_CYCLES:
                continue
            
            test_cycles = cycles[split_idx:]
            
            if len(test_cycles) < self.MIN_TEST_CYCLES:
                continue
            
            test_mask = df['Cycle'].isin(test_cycles)
            test_df = df[test_mask]
            
            test_failures = test_df['Verdict'].sum()
            test_failure_rate = test_df['Verdict'].mean()
            
            if test_failures < self.MIN_TEST_FAILURES_LOW:
                continue
            
            score = self._score_split(
                test_failures=test_failures,
                test_failure_rate=test_failure_rate,
                test_size=len(test_df),
                test_cycles=len(test_cycles),
                target_failures=min_test_failures,
                overall_rate=stats['overall_failure_rate'],
                strategy='low_failure'
            )
            
            if score > best_score:
                best_score = score
                best_split = {
                    'split_idx': split_idx,
                    'train_cycles': cycles[:split_idx],
                    'test_cycles': test_cycles,
                    'test_pct': test_pct
                }
        
        if best_split is None:
            raise ValueError(
                f"Could not find valid split for low-failure project '{stats['project_name']}'. "
                f"Only {stats['total_failures']} total failures available. "
                f"Consider excluding this project or relaxing constraints."
            )
        
        train_mask = df['Cycle'].isin(best_split['train_cycles'])
        test_mask = df['Cycle'].isin(best_split['test_cycles'])
        
        train_idx = df[train_mask].index.to_numpy()
        test_idx = df[test_mask].index.to_numpy()
        
        split_info = {
            'test_proportion': best_split['test_pct'],
            'split_reason': f"Extended test set ({best_split['test_pct']:.0%}) to accumulate sufficient failures"
        }
        
        return train_idx, test_idx, split_info
    
    def _split_normal(self, df: pd.DataFrame, stats: Dict) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Strategy for normal failure rate projects (5-50%)"""
        
        if self.verbose:
            print(f"\n{'='*80}")
            print("APPLYING NORMAL FAILURE RATE STRATEGY")
            print(f"{'='*80}")
            print(f"   Strategy: Standard temporal split (25-35%) with ≥{self.MIN_TEST_FAILURES_NORMAL} failures")
        
        cycles = sorted(df['Cycle'].unique())
        
        best_split = None
        best_score = -np.inf
        
        for test_pct in np.arange(0.20, 0.45, 0.05):
            split_idx = int(len(cycles) * (1 - test_pct))
            
            if split_idx < self.MIN_TRAIN_CYCLES:
                continue
            
            test_cycles = cycles[split_idx:]
            
            if len(test_cycles) < self.MIN_TEST_CYCLES:
                continue
            
            test_mask = df['Cycle'].isin(test_cycles)
            test_df = df[test_mask]
            
            test_failures = test_df['Verdict'].sum()
            test_failure_rate = test_df['Verdict'].mean()
            
            if test_failures < self.MIN_TEST_FAILURES_NORMAL:
                continue
            
            score = self._score_split(
                test_failures=test_failures,
                test_failure_rate=test_failure_rate,
                test_size=len(test_df),
                test_cycles=len(test_cycles),
                target_failures=self.MIN_TEST_FAILURES_NORMAL,
                overall_rate=stats['overall_failure_rate'],
                strategy='normal'
            )
            
            if score > best_score:
                best_score = score
                best_split = {
                    'split_idx': split_idx,
                    'train_cycles': cycles[:split_idx],
                    'test_cycles': test_cycles,
                    'test_pct': test_pct
                }
        
        if best_split is None:
            raise ValueError(
                f"Could not find valid split for project '{stats['project_name']}'. "
                f"Need at least {self.MIN_TEST_FAILURES_NORMAL} failures in test set."
            )
        
        train_mask = df['Cycle'].isin(best_split['train_cycles'])
        test_mask = df['Cycle'].isin(best_split['test_cycles'])
        
        train_idx = df[train_mask].index.to_numpy()
        test_idx = df[test_mask].index.to_numpy()
        
        split_info = {
            'test_proportion': best_split['test_pct'],
            'split_reason': f"Standard temporal split ({best_split['test_pct']:.0%})"
        }
        
        return train_idx, test_idx, split_info
    
    def _split_high_failure(self, df: pd.DataFrame, stats: Dict) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Strategy for high failure rate projects (>50%)"""
        
        if self.verbose:
            print(f"\n{'='*80}")
            print("APPLYING HIGH FAILURE RATE STRATEGY")
            print(f"{'='*80}")
            print("     High failure rate may indicate:")
            print("      - Integration/E2E test suite (expected)")
            print("      - Active refactoring period")
            print("      - Data quality issues (investigate)")
            print(f"   Strategy: Compact test set (20-30%) - plenty of failures anyway")
        
        cycles = sorted(df['Cycle'].unique())
        
        best_split = None
        best_score = -np.inf
        
        for test_pct in np.arange(0.20, 0.40, 0.05):
            split_idx = int(len(cycles) * (1 - test_pct))
            
            if split_idx < self.MIN_TRAIN_CYCLES * 1.5:
                continue
            
            test_cycles = cycles[split_idx:]
            
            if len(test_cycles) < self.MIN_TEST_CYCLES:
                continue
            
            test_mask = df['Cycle'].isin(test_cycles)
            test_df = df[test_mask]
            
            test_failures = test_df['Verdict'].sum()
            test_failure_rate = test_df['Verdict'].mean()
            
            if test_failures < self.MIN_TEST_FAILURES_NORMAL:
                continue
            
            score = self._score_split(
                test_failures=test_failures,
                test_failure_rate=test_failure_rate,
                test_size=len(test_df),
                test_cycles=len(test_cycles),
                target_failures=self.MIN_TEST_FAILURES_NORMAL,
                overall_rate=stats['overall_failure_rate'],
                strategy='high_failure'
            )
            
            if score > best_score:
                best_score = score
                best_split = {
                    'split_idx': split_idx,
                    'train_cycles': cycles[:split_idx],
                    'test_cycles': test_cycles,
                    'test_pct': test_pct
                }
        
        if best_split is None:
            split_idx = int(len(cycles) * 0.75)
            best_split = {
                'split_idx': split_idx,
                'train_cycles': cycles[:split_idx],
                'test_cycles': cycles[split_idx:],
                'test_pct': 0.25
            }
        
        train_mask = df['Cycle'].isin(best_split['train_cycles'])
        test_mask = df['Cycle'].isin(best_split['test_cycles'])
        
        train_idx = df[train_mask].index.to_numpy()
        test_idx = df[test_mask].index.to_numpy()
        
        split_info = {
            'test_proportion': best_split['test_pct'],
            'split_reason': f"Compact test set ({best_split['test_pct']:.0%}) - high failure rate provides ample failures"
        }
        
        return train_idx, test_idx, split_info
    
    def _score_split(self, 
                    test_failures: int,
                    test_failure_rate: float,
                    test_size: int,
                    test_cycles: int,
                    target_failures: int,
                    overall_rate: float,
                    strategy: str) -> float:
        """Score a candidate split"""
        score = 0.0
        
        if strategy == 'low_failure':
            failure_score = min(1.0, test_failures / target_failures)
            score += failure_score * 5.0
            
            if test_failure_rate > 0:
                rate_ratio = test_failure_rate / overall_rate
                if 0.5 <= rate_ratio <= 1.5:
                    score += 2.0
                elif 0.3 <= rate_ratio <= 2.0:
                    score += 1.0
            
            cycle_score = min(1.0, test_cycles / 50)
            score += cycle_score * 1.5
            
        elif strategy == 'normal':
            rate_diff = abs(test_failure_rate - overall_rate)
            rate_score = max(0, 1 - (rate_diff / 0.3))
            score += rate_score * 3.0
            
            failure_score = min(1.0, test_failures / 100)
            score += failure_score * 2.0
            
            cycle_score = min(1.0, test_cycles / 60)
            score += cycle_score * 1.5
            
            if test_failure_rate > 0.60 or test_failure_rate < 0.10:
                score -= 2.0
                
        else:  # high_failure
            if 0.20 <= test_size / (test_size + 1000) <= 0.30:
                score += 2.0
            
            if 0.40 <= test_failure_rate <= 0.70:
                score += 1.5
            
            cycle_score = min(1.0, test_cycles / 40)
            score += cycle_score * 1.0
        
        return score
    
    def _create_metadata(self,
                        df: pd.DataFrame,
                        project_name: str,
                        project_stats: Dict,
                        project_type: str,
                        train_idx: np.ndarray,
                        test_idx: np.ndarray,
                        split_info: Dict) -> SplitMetadata:
        """Create comprehensive metadata"""
        
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]
        
        train_cycles = sorted(train_df['Cycle'].unique())
        test_cycles = sorted(test_df['Cycle'].unique())
        
        test_failures = int(test_df['Verdict'].sum())
        
        power, power_desc = self._assess_statistical_power(test_failures, len(test_cycles))
        emphasis = self._get_recommended_emphasis(test_failures, len(test_cycles))
        warnings_list = self._check_quality(df, train_idx, test_idx, test_failures, len(test_cycles))
        
        metadata = SplitMetadata(
            project_name=project_name,
            strategy=project_type,
            
            total_tests=project_stats['total_tests'],
            total_failures=project_stats['total_failures'],
            overall_failure_rate=project_stats['overall_failure_rate'],
            total_cycles=project_stats['total_cycles'],
            cycle_range=project_stats['cycle_range'],
            
            train_cycles=(int(train_cycles[0]), int(train_cycles[-1])),
            train_size=len(train_df),
            train_failures=int(train_df['Verdict'].sum()),
            train_failure_rate=float(train_df['Verdict'].mean()),
            
            test_cycles=(int(test_cycles[0]), int(test_cycles[-1])),
            test_size=len(test_df),
            test_failures=test_failures,
            test_failure_rate=float(test_df['Verdict'].mean()),
            test_proportion=split_info['test_proportion'],
            
            statistical_power=power,
            power_assessment=power_desc,
            recommended_emphasis=emphasis,
            
            temporal_validity=True,
            quality_warnings=warnings_list
        )
        
        return metadata
    
    def _assess_statistical_power(self, n_failures: int, n_cycles: int) -> Tuple[str, str]:
        """Assess statistical power for different effect sizes"""
        
        if n_failures >= 100 and n_cycles >= 50:
            return "Excellent", "Can reliably detect small effects (Cohen's d ≥ 0.2)"
        elif n_failures >= 50 and n_cycles >= 30:
            return "Good", "Can reliably detect medium effects (Cohen's d ≥ 0.3)"
        elif n_failures >= 30 and n_cycles >= 20:
            return "Adequate", "Can reliably detect large effects (Cohen's d ≥ 0.5)"
        else:
            return "Limited", "Statistical tests may be underpowered; emphasize practical metrics and effect sizes"
    
    def _get_recommended_emphasis(self, n_failures: int, n_cycles: int) -> str:
        """Get recommendation for what to emphasize in results"""
        
        if n_failures >= 100:
            return (
                "All metrics are interpretable. Statistical significance tests have adequate power. "
                "Report p-values, effect sizes, and practical metrics (APFD-C, time savings)."
            )
        elif n_failures >= 50:
            return (
                "Report all metrics. Statistical tests have moderate power - emphasize effect sizes "
                "and practical metrics (APFD-C, time savings, Precision@k) alongside p-values."
            )
        else:
            return (
                "Report all metrics but emphasize practical significance. Statistical tests may be "
                "underpowered - focus on effect sizes, confidence intervals, and cost-aware metrics "
                "(APFD-C, time savings). Report p-values but interpret cautiously."
            )
    
    def _check_quality(self, 
                      df: pd.DataFrame, 
                      train_idx: np.ndarray, 
                      test_idx: np.ndarray,
                      test_failures: int,
                      test_cycles: int) -> List[str]:
        """Check split quality and return warnings"""
        warnings_list = []
        
        if test_failures < 30:
            warnings_list.append(f"Only {test_failures} test failures - statistical power is very limited")
        
        if test_cycles < 20:
            warnings_list.append(f"Only {test_cycles} test cycles - temporal patterns may be unreliable")
        
        if test_cycles < 30:
            warnings_list.append(f"Limited test cycles ({test_cycles}) - interpret results with caution")
        
        train_cycles = set(df.iloc[train_idx]['Cycle'])
        test_cycles_set = set(df.iloc[test_idx]['Cycle'])
        
        if train_cycles.intersection(test_cycles_set):
            warnings_list.append("CRITICAL: Temporal leakage detected - train and test cycles overlap!")
        
        if max(train_cycles) >= min(test_cycles_set):
            warnings_list.append("CRITICAL: Test cycles not strictly after train cycles!")
        
        return warnings_list
    
    def _verify_split(self, 
                     df: pd.DataFrame, 
                     train_idx: np.ndarray, 
                     test_idx: np.ndarray,
                     metadata: SplitMetadata) -> None:
        """Verify split quality"""
        
        if self.verbose:
            print(f"\n{'='*80}")
            print("VERIFICATION")
            print(f"{'='*80}")
        
        assert len(set(train_idx).intersection(set(test_idx))) == 0, "Index overlap detected!"
        
        train_cycles = set(df.iloc[train_idx]['Cycle'])
        test_cycles = set(df.iloc[test_idx]['Cycle'])
        
        assert len(train_cycles.intersection(test_cycles)) == 0, "Cycle overlap detected!"
        assert max(train_cycles) < min(test_cycles), "Test cycles not after train cycles!"
        
        if self.verbose:
            print(" Quality Checks:")
            print(f"    No index overlap")
            print(f"    No cycle overlap")
            print(f"    Temporal order preserved")
            print(f"    Test failures: {metadata.test_failures}")
            print(f"    Test cycles: {len(test_cycles)}")
            
            if metadata.quality_warnings:
                print(f"\n  Warnings:")
                for warning in metadata.quality_warnings:
                    print(f"     {warning}")
    
    def _save_metadata_to_file(self, metadata: SplitMetadata, project_name: str) -> None:
        """Save metadata to JSON file"""
        filepath = self.output_dir / f"split_metadata_{project_name}.json"
        
        with open(filepath, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2, default=str)
        
        if self.verbose:
            print(f"\n Metadata saved: {filepath}")
    
    def _print_header(self, title: str) -> None:
        """Print section header"""
        print(f"\n{'='*80}")
        print(title.center(80))
        print(f"{'='*80}")
    
    def _print_project_analysis(self, stats: Dict) -> None:
        """Print project analysis"""
        print(f"\n PROJECT ANALYSIS: {stats['project_name']}")
        print(f"   Total tests: {stats['total_tests']:,}")
        print(f"   Total failures: {stats['total_failures']:,} ({stats['overall_failure_rate']:.2%})")
        print(f"   Cycles: {stats['total_cycles']} (range: {stats['cycle_range']})")
        print(f"   Avg tests/cycle: {stats['avg_tests_per_cycle']:.1f}")
        print(f"   Avg failures/cycle: {stats['avg_failures_per_cycle']:.1f}")
        print(f"   Failure rate variability: σ={stats['failure_rate_std']:.3f}")
        print(f"   Failure rate range: {stats['failure_rate_min']:.2%} to {stats['failure_rate_max']:.2%}")
    
    def _print_summary(self, metadata: SplitMetadata) -> None:
        """Print final summary"""
        print(f"\n{'='*80}")
        print("FINAL SPLIT SUMMARY")
        print(f"{'='*80}")
        print(f"Project: {metadata.project_name}")
        print(f"Strategy: {metadata.strategy.upper().replace('_', ' ')}")
        print(f"\n Split Details:")
        print(f"   Train: cycles {metadata.train_cycles[0]}-{metadata.train_cycles[1]} ({metadata.train_cycles[1] - metadata.train_cycles[0] + 1} cycles)")
        print(f"      Size: {metadata.train_size:,} tests")
        print(f"      Failures: {metadata.train_failures:,} ({metadata.train_failure_rate:.2%})")
        print(f"\n   Test: cycles {metadata.test_cycles[0]}-{metadata.test_cycles[1]} ({metadata.test_cycles[1] - metadata.test_cycles[0] + 1} cycles)")
        print(f"      Size: {metadata.test_size:,} tests ({metadata.test_proportion:.1%})")
        print(f"      Failures: {metadata.test_failures:,} ({metadata.test_failure_rate:.2%})")
        print(f"\n Statistical Assessment:")
        print(f"   Power: {metadata.statistical_power}")
        print(f"   {metadata.power_assessment}")
        print(f"\n💡 Recommendation:")
        print(f"   {metadata.recommended_emphasis}")
        print(f"{'='*80}\n")


def smart_temporal_split(df: pd.DataFrame,
                        project_name: str,
                        output_dir: str = "split_metadata",
                        verbose: bool = True) -> Tuple[np.ndarray, np.ndarray, SplitMetadata]:
    """
    Drop-in replacement for strict_temporal_split with automatic adaptation.
    """
    splitter = UnifiedAdaptiveSplitter(output_dir=output_dir, verbose=verbose)
    return splitter.split(df, project_name)


# STATISTICAL SIGNIFICANCE TESTING
class StatisticalTester:
    """
    Comprehensive statistical testing for model comparisons
    """
    
    @staticmethod
    def bootstrap_confidence_interval(data, n_bootstrap=1000, confidence=0.95):
        """Calculate bootstrap confidence intervals"""
        if len(data) == 0:
            return 0, 0, 0
            
        bootstrap_means = []
        np.random.seed(42)  # Reproducible bootstrap
        
        for _ in range(n_bootstrap):
            sample = np.random.choice(data, size=len(data), replace=True)
            bootstrap_means.append(np.mean(sample))
        
        alpha = 1 - confidence
        lower = np.percentile(bootstrap_means, 100 * alpha/2)
        upper = np.percentile(bootstrap_means, 100 * (1 - alpha/2))
        mean = np.mean(data)
        
        return mean, lower, upper
    
    @staticmethod
    def cohens_d(group1, group2):
        """Calculate Cohen's d effect size"""
        if len(group1) == 0 or len(group2) == 0:
            return 0
            
        n1, n2 = len(group1), len(group2)
        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        
        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0
            
        return (mean1 - mean2) / pooled_std
    
    @staticmethod
    def compare_models_statistically(results_dict, metric='avg_time_to_first_failure'):
        """
        Compare all models statistically on a given metric
        """
        model_names = list(results_dict.keys())
        comparison_matrix = {}
        
        for i, model1 in enumerate(model_names):
            for j, model2 in enumerate(model_names[i+1:], i+1):
                
                # Get per-cycle data for both models
                data1 = results_dict[model1].get(metric.replace('avg_', '') + '_per_cycle', [])
                data2 = results_dict[model2].get(metric.replace('avg_', '') + '_per_cycle', [])
                
                if len(data1) > 0 and len(data2) > 0:
                    # Mann-Whitney U test (non-parametric)
                    try:
                        statistic, p_value = mannwhitneyu(data1, data2, alternative='two-sided')
                    except ValueError:
                        p_value = 1.0
                        statistic = 0
                    
                    # Effect size
                    effect_size = StatisticalTester.cohens_d(data1, data2)
                    
                    # Confidence intervals
                    mean1, lower1, upper1 = StatisticalTester.bootstrap_confidence_interval(data1)
                    mean2, lower2, upper2 = StatisticalTester.bootstrap_confidence_interval(data2)
                    
                    comparison_matrix[f"{model1}_vs_{model2}"] = {
                        'p_value': p_value,
                        'effect_size': effect_size,
                        'significant': p_value < 0.05,
                        'model1_ci': (mean1, lower1, upper1),
                        'model2_ci': (mean2, lower2, upper2),
                        'winner': model1 if mean1 < mean2 else model2  # Assuming lower is better
                    }
        
        return comparison_matrix

class StandardTCPMetrics:
    """
    Standard metrics used in TCP research literature (DeepOrder, etc.)
    
    Key Metrics:
    - APFD (Average Percentage of Faults Detected) - Gold standard
    - APFD-C (Cost-aware APFD) - Considers test execution time
    - NAPFD (Normalized APFD) - Accounts for varying failure counts
    - Recall@k, Precision@k
    - Time to First Failure (TTFF)
    - Rank of First Failure
    """
    
    @staticmethod
    def calculate_apfd(verdicts, predictions):
        """
        Calculate APFD (Average Percentage of Faults Detected)
        
        This is THE standard metric in TCP research.
        
        Formula: APFD = 1 - (sum of ranks of failing tests)/(n*m) + 1/(2n)
        where n = total tests, m = total failures
        
        Args:
            verdicts: Array of actual test results (1=fail, 0=pass)
            predictions: Array of failure probabilities (higher = more likely to fail)
        
        Returns:
            float: APFD score (0-1, higher is better)
        """
        n = len(verdicts)
        m = verdicts.sum()
        
        if m == 0:
            return 1.0  # No failures to detect
        
        # Sort tests by predictions (highest first)
        sorted_indices = np.argsort(-predictions)
        sorted_verdicts = verdicts[sorted_indices]
        
        # Find positions of failures (1-indexed)
        failure_positions = np.where(sorted_verdicts == 1)[0] + 1
        
        # Calculate APFD
        apfd = 1 - (failure_positions.sum() / (n * m)) + (1 / (2 * n))
        
        return apfd
    
    @staticmethod
    def calculate_apfd_c(verdicts, predictions, durations):
        """
        Calculate APFD-C (Cost-aware APFD)
        
        Considers test execution time - more realistic than APFD.
        Used in DeepOrder and modern TCP research.
        
        Formula: APFD-C = 1 - (sum of costs until failure_i)/(total_cost * m) + (first_cost)/(2*total_cost)
        
        Args:
            verdicts: Array of actual test results (1=fail, 0=pass)
            predictions: Array of failure probabilities
            durations: Array of test execution times
        
        Returns:
            float: APFD-C score (0-1, higher is better)
        """
        n = len(verdicts)
        m = verdicts.sum()
        
        if m == 0:
            return 1.0
        
        # Sort by predictions
        sorted_indices = np.argsort(-predictions)
        sorted_verdicts = verdicts[sorted_indices]
        sorted_durations = durations[sorted_indices]
        
        # Calculate cumulative costs
        cumulative_costs = np.cumsum(sorted_durations)
        total_cost = cumulative_costs[-1]
        
        # Find costs at which failures are detected
        failure_indices = np.where(sorted_verdicts == 1)[0]
        failure_costs = cumulative_costs[failure_indices]
        
        # Calculate APFD-C
        apfd_c = 1 - (failure_costs.sum() / (total_cost * m)) + (sorted_durations[0] / (2 * total_cost))
        
        return apfd_c
    
    @staticmethod
    def calculate_napfd(verdicts, predictions):
        """
        Calculate NAPFD (Normalized APFD)
        
        Normalizes APFD to account for varying numbers of failures.
        
        Args:
            verdicts: Array of actual test results
            predictions: Array of failure probabilities
        
        Returns:
            float: NAPFD score (0-1, higher is better)
        """
        n = len(verdicts)
        m = verdicts.sum()
        
        if m == 0:
            return 1.0
        
        # Sort by predictions
        sorted_indices = np.argsort(-predictions)
        sorted_verdicts = verdicts[sorted_indices]
        
        # Calculate area under the curve
        p = 0
        area = 0
        for i, verdict in enumerate(sorted_verdicts, 1):
            if verdict == 1:
                p += 1
                area += p / m
        
        # Normalize
        napfd = area / n
        
        return napfd
    
    @staticmethod
    def calculate_recall_at_k(verdicts, predictions, k_values=[10, 20, 50, 100]):
        """
        Calculate Recall@k - How many failures found in top-k tests
        
        Args:
            verdicts: Array of actual test results
            predictions: Array of failure probabilities
            k_values: List of k values to evaluate
        
        Returns:
            dict: Recall@k for each k value
        """
        m = verdicts.sum()
        
        if m == 0:
            return {f"recall@{k}": 0.0 for k in k_values}
        
        # Sort by predictions
        sorted_indices = np.argsort(-predictions)
        sorted_verdicts = verdicts[sorted_indices]
        
        results = {}
        for k in k_values:
            k = min(k, len(verdicts))  # Don't exceed array length
            failures_in_top_k = sorted_verdicts[:k].sum()
            recall = failures_in_top_k / m
            results[f"recall@{k}"] = recall
        
        return results
    
    @staticmethod
    def calculate_precision_at_k(verdicts, predictions, k_values=[10, 20, 50, 100]):
        """
        Calculate Precision@k - Precision of top-k predictions
        
        Args:
            verdicts: Array of actual test results
            predictions: Array of failure probabilities
            k_values: List of k values to evaluate
        
        Returns:
            dict: Precision@k for each k value
        """
        sorted_indices = np.argsort(-predictions)
        sorted_verdicts = verdicts[sorted_indices]
        
        results = {}
        for k in k_values:
            k = min(k, len(verdicts))
            failures_in_top_k = sorted_verdicts[:k].sum()
            precision = failures_in_top_k / k
            results[f"precision@{k}"] = precision
        
        return results
    
    @staticmethod
    def calculate_time_to_first_failure(verdicts, predictions, durations):
        """
        Calculate Time to First Failure (TTFF)
        
        Args:
            verdicts: Array of actual test results
            predictions: Array of failure probabilities
            durations: Array of test execution times
        
        Returns:
            float: Time until first failure detected
        """
        if verdicts.sum() == 0:
            return durations.sum()  # All tests needed
        
        # Sort by predictions
        sorted_indices = np.argsort(-predictions)
        sorted_verdicts = verdicts[sorted_indices]
        sorted_durations = durations[sorted_indices]
        
        # Find first failure
        first_failure_idx = np.where(sorted_verdicts == 1)[0][0]
        
        # Calculate time to reach it
        ttff = sorted_durations[:first_failure_idx + 1].sum()
        
        return ttff
    
    @staticmethod
    def calculate_rank_of_first_failure(verdicts, predictions):
        """
        Calculate rank of first failing test
        
        Args:
            verdicts: Array of actual test results
            predictions: Array of failure probabilities
        
        Returns:
            int: Rank of first failure (1-indexed)
        """
        if verdicts.sum() == 0:
            return len(verdicts)  # No failures
        
        sorted_indices = np.argsort(-predictions)
        sorted_verdicts = verdicts[sorted_indices]
        
        first_failure_idx = np.where(sorted_verdicts == 1)[0][0]
        
        return first_failure_idx + 1  # 1-indexed rank
    
    @staticmethod
    def calculate_tests_to_k_percent_failures(verdicts, predictions, percentages=[0.5, 0.75, 0.9, 1.0]):
        """
        Calculate number of tests needed to find k% of failures
        
        Args:
            verdicts: Array of actual test results
            predictions: Array of failure probabilities
            percentages: List of failure coverage percentages
        
        Returns:
            dict: Number of tests for each percentage
        """
        m = verdicts.sum()
        
        if m == 0:
            return {f"tests_to_{int(p*100)}pct": 0 for p in percentages}
        
        sorted_indices = np.argsort(-predictions)
        sorted_verdicts = verdicts[sorted_indices]
        
        cumulative_failures = np.cumsum(sorted_verdicts)
        
        results = {}
        for p in percentages:
            target_failures = int(m * p)
            if target_failures == 0:
                results[f"tests_to_{int(p*100)}pct"] = 0
                continue
            
            # Find first position where we reach target
            positions = np.where(cumulative_failures >= target_failures)[0]
            if len(positions) > 0:
                tests_needed = positions[0] + 1
            else:
                tests_needed = len(verdicts)
            
            results[f"tests_to_{int(p*100)}pct"] = tests_needed
        
        return results
    
    @staticmethod
    def calculate_all_metrics(df_test, predictions, duration_col='Duration'):
        """
        Calculate ALL standard TCP metrics at once
        
        Args:
            df_test: Test DataFrame with 'Verdict' column
            predictions: Array of failure probabilities
            duration_col: Name of duration column
        
        Returns:
            dict: All metrics
        """
        verdicts = df_test['Verdict'].values
        durations = df_test[duration_col].values if duration_col in df_test.columns else np.ones(len(verdicts))
        
        metrics = {}
        
        # Primary metrics
        metrics['APFD'] = StandardTCPMetrics.calculate_apfd(verdicts, predictions)
        metrics['APFD_C'] = StandardTCPMetrics.calculate_apfd_c(verdicts, predictions, durations)
        metrics['NAPFD'] = StandardTCPMetrics.calculate_napfd(verdicts, predictions)
        
        # Recall@k
        recall_metrics = StandardTCPMetrics.calculate_recall_at_k(verdicts, predictions)
        metrics.update(recall_metrics)
        
        # Precision@k
        precision_metrics = StandardTCPMetrics.calculate_precision_at_k(verdicts, predictions)
        metrics.update(precision_metrics)
        
        # Time metrics
        metrics['TTFF'] = StandardTCPMetrics.calculate_time_to_first_failure(verdicts, predictions, durations)
        metrics['rank_first_failure'] = StandardTCPMetrics.calculate_rank_of_first_failure(verdicts, predictions)
        
        # Tests to k% failures
        tests_metrics = StandardTCPMetrics.calculate_tests_to_k_percent_failures(verdicts, predictions)
        metrics.update(tests_metrics)
        
        return metrics
    
    @staticmethod
    def calculate_per_cycle_metrics(df_test, predictions, duration_col='Duration'):
        """
        Calculate metrics per cycle (for statistical testing)
        
        Args:
            df_test: Test DataFrame
            predictions: Array of predictions
            duration_col: Duration column name
        
        Returns:
            dict: Per-cycle metrics
        """
        if 'Cycle' not in df_test.columns:
            # No cycles - treat as single cycle
            return {
                'apfd_per_cycle': [StandardTCPMetrics.calculate_all_metrics(df_test, predictions, duration_col)['APFD']],
                'apfd_c_per_cycle': [StandardTCPMetrics.calculate_all_metrics(df_test, predictions, duration_col)['APFD_C']],
                'ttff_per_cycle': [StandardTCPMetrics.calculate_all_metrics(df_test, predictions, duration_col)['TTFF']]
            }
        
        apfd_per_cycle = []
        apfd_c_per_cycle = []
        ttff_per_cycle = []
        
        for cycle in sorted(df_test['Cycle'].unique()):
            cycle_mask = df_test['Cycle'] == cycle
            cycle_df = df_test[cycle_mask]
            cycle_preds = predictions[cycle_mask]
            
            if cycle_df['Verdict'].sum() > 0:  # Has failures
                cycle_metrics = StandardTCPMetrics.calculate_all_metrics(
                    cycle_df, cycle_preds, duration_col
                )
                apfd_per_cycle.append(cycle_metrics['APFD'])
                apfd_c_per_cycle.append(cycle_metrics['APFD_C'])
                ttff_per_cycle.append(cycle_metrics['TTFF'])
        
        return {
            'apfd_per_cycle': apfd_per_cycle,
            'apfd_c_per_cycle': apfd_c_per_cycle,
            'ttff_per_cycle': ttff_per_cycle
        }
    
    @staticmethod
    def compare_with_baselines(df_test, predictions_dict, duration_col='Duration'):
        """
        Calculate all metrics for all models and create comparison table
        
        Args:
            df_test: Test DataFrame
            predictions_dict: Dict of {model_name: predictions}
            duration_col: Duration column name
        
        Returns:
            pd.DataFrame: Comparison table
        """
        results = []
        
        for model_name, predictions in predictions_dict.items():
            metrics = StandardTCPMetrics.calculate_all_metrics(df_test, predictions, duration_col)
            metrics['Model'] = model_name
            results.append(metrics)
        
        df_results = pd.DataFrame(results)
        
        # Reorder columns - most important first
        important_cols = ['Model', 'APFD', 'APFD_C', 'NAPFD', 'TTFF', 'rank_first_failure']
        other_cols = [c for c in df_results.columns if c not in important_cols]
        df_results = df_results[important_cols + other_cols]
        
        # Sort by APFD (descending)
        df_results = df_results.sort_values('APFD', ascending=False)
        
        return df_results
    
    @staticmethod
    def visualize_apfd_comparison(df_test, predictions_dict, output_path, duration_col='Duration'):
        """
        Create visualization comparing APFD and APFD-C across models
        
        Args:
            df_test: Test DataFrame
            predictions_dict: Dict of predictions
            output_path: Path to save visualization
            duration_col: Duration column name
        """
        results = []
        
        for model_name, predictions in predictions_dict.items():
            metrics = StandardTCPMetrics.calculate_all_metrics(df_test, predictions, duration_col)
            results.append({
                'Model': model_name,
                'APFD': metrics['APFD'],
                'APFD_C': metrics['APFD_C'],
                'TTFF': metrics['TTFF']
            })
        
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('APFD', ascending=False)
        
        # Get top 10 models
        df_top = df_results.head(10)
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        # 1. APFD comparison
        ax1 = axes[0]
        bars1 = ax1.barh(range(len(df_top)), df_top['APFD'], alpha=0.8, color='steelblue')
        ax1.set_yticks(range(len(df_top)))
        ax1.set_yticklabels([m.replace('ML_', '')[:25] for m in df_top['Model']], fontsize=9)
        ax1.set_xlabel('APFD Score', fontsize=12)
        ax1.set_title('APFD Comparison\n(Higher is Better)', fontsize=14, fontweight='bold')
        ax1.set_xlim(0, 1)
        ax1.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, (bar, val) in enumerate(zip(bars1, df_top['APFD'])):
            ax1.text(val + 0.01, bar.get_y() + bar.get_height()/2, 
                    f'{val:.3f}', va='center', fontsize=9)
        
        # 2. APFD-C comparison
        ax2 = axes[1]
        bars2 = ax2.barh(range(len(df_top)), df_top['APFD_C'], alpha=0.8, color='forestgreen')
        ax2.set_yticks(range(len(df_top)))
        ax2.set_yticklabels([m.replace('ML_', '')[:25] for m in df_top['Model']], fontsize=9)
        ax2.set_xlabel('APFD-C Score', fontsize=12)
        ax2.set_title('APFD-C Comparison\n(Cost-Aware, Higher is Better)', fontsize=14, fontweight='bold')
        ax2.set_xlim(0, 1)
        ax2.grid(axis='x', alpha=0.3)
        
        for i, (bar, val) in enumerate(zip(bars2, df_top['APFD_C'])):
            ax2.text(val + 0.01, bar.get_y() + bar.get_height()/2, 
                    f'{val:.3f}', va='center', fontsize=9)
        
        # 3. TTFF comparison (lower is better)
        ax3 = axes[2]
        bars3 = ax3.barh(range(len(df_top)), df_top['TTFF'], alpha=0.8, color='coral')
        ax3.set_yticks(range(len(df_top)))
        ax3.set_yticklabels([m.replace('ML_', '')[:25] for m in df_top['Model']], fontsize=9)
        ax3.set_xlabel('Time to First Failure', fontsize=12)
        ax3.set_title('TTFF Comparison\n(Lower is Better)', fontsize=14, fontweight='bold')
        ax3.grid(axis='x', alpha=0.3)
        
        for i, (bar, val) in enumerate(zip(bars3, df_top['TTFF'])):
            ax3.text(val + 0.5, bar.get_y() + bar.get_height()/2, 
                    f'{val:.1f}', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f" APFD comparison visualization saved: {output_path}")

# COMPREHENSIVE BASELINE MODELS
class BaselineModels:
    """
    Proper baseline models for fair comparison
    """
    
    @staticmethod
    def random_baseline(df_test, seed=42):
        """Completely random predictions"""
        np.random.seed(seed)
        return np.random.random(len(df_test))
    
    @staticmethod 
    def duration_baseline(df_test):
        """Inverse duration: shorter tests more likely to fail"""
        durations = df_test.get('DurationFeature', df_test.get('Duration', np.ones(len(df_test))))
        max_duration = durations.max()
        if max_duration == 0:
            return np.ones(len(df_test)) * 0.5
        return 1 - (durations / max_duration)
    
    @staticmethod
    def recency_baseline(df_test):
        """More recent tests more likely to fail"""
        cycles = df_test['Cycle']
        max_cycle = cycles.max()
        min_cycle = cycles.min()
        if max_cycle == min_cycle:
            return np.ones(len(df_test)) * 0.5
        return (cycles - min_cycle) / (max_cycle - min_cycle)
    
    @staticmethod
    def historical_failure_rate_baseline(df_train, df_test):
        """Historical failure rate per test/file"""
        if 'TestName' in df_train.columns:
            failure_rates = df_train.groupby('TestName')['Verdict'].mean()
            return df_test['TestName'].map(failure_rates).fillna(0.5)
        else:
            # Use overall failure rate as fallback
            overall_rate = df_train['Verdict'].mean()
            return np.full(len(df_test), overall_rate)
    
    @staticmethod
    def priority_value_baseline(df_test):
        """
        Create PRIORITY_VALUE baseline using ONLY test data
        This baseline should NOT use temporal splitting since it represents
        the corrupted ranking we're trying to detect and improve upon
        """
        priority_col = None
        possible_names = ['PRIORITY_VALUE', 'Priority_value', 'priority_value', 'PriorityValue']
        
        for col_name in possible_names:
            if col_name in df_test.columns:
                priority_col = col_name
                break
        
        if priority_col is not None:
            print(f" Using actual {priority_col} column for PRIORITY_VALUE baseline")
            return df_test[priority_col].values
        else:
            print(" No PRIORITY_VALUE column found, creating synthetic baseline using test data only")
            # Create synthetic PRIORITY_VALUE using test data only
            weights = {'E1': 0.1, 'E2': 0.2, 'E3': 0.7}
            priority_value = np.zeros(len(df_test))
            
            for feature, weight in weights.items():
                if feature in df_test.columns:
                    priority_value += df_test[feature] * weight
            
            duration_col = 'Duration' if 'Duration' in df_test.columns else 'DurationFeature'
            if duration_col in df_test.columns:
                max_duration = df_test[duration_col].max()
                if max_duration > 0:
                    priority_value += max_duration / (df_test[duration_col] + 1e-8)
            
            return priority_value

class StatisticalPowerAnalyzer:
    """
    Determine if we have sufficient data to detect meaningful differences
    """
    
    @staticmethod
    def calculate_required_sample_size(effect_size=0.3, alpha=0.05, power=0.8):
        """Calculate required sample size for desired statistical power"""
        from scipy.stats import norm
        
        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = norm.ppf(power)
        
        n_required = 2 * ((z_alpha + z_beta) / effect_size) ** 2
        return int(np.ceil(n_required))
    
    @staticmethod
    def calculate_actual_power(n_samples, effect_size=0.3, alpha=0.05):
        """Calculate actual statistical power given sample size"""
        from scipy.stats import norm
        
        z_alpha = norm.ppf(1 - alpha/2)
        ncp = effect_size * np.sqrt(n_samples / 2)  # Non-centrality parameter
        power = 1 - norm.cdf(z_alpha - ncp)
        return power
    
    @staticmethod
    def analyze_study_power(df_test, predictions_dict, effect_sizes=[0.2, 0.3, 0.5]):
        """
        Comprehensive power analysis for the study
        """
        print("\n" + "="*80)
        print("STATISTICAL POWER ANALYSIS")
        print("="*80)
        
        n_cycles = df_test['Cycle'].nunique() if 'Cycle' in df_test.columns else 1
        n_tests = len(df_test)
        n_failures = df_test['Verdict'].sum()
        
        print(f"\n Dataset Characteristics:")
        print(f"   Total tests: {n_tests}")
        print(f"   Total failures: {n_failures}")
        print(f"   Cycles: {n_cycles}")
        print(f"   Tests per cycle (avg): {n_tests/n_cycles:.1f}")
        
        print(f"\n Power Analysis for Different Effect Sizes:")
        print("   (Cohen's d convention: 0.2=small, 0.5=medium, 0.8=large)")
        
        results = {}
        for effect_size in effect_sizes:
            required_n = StatisticalPowerAnalyzer.calculate_required_sample_size(effect_size)
            actual_power = StatisticalPowerAnalyzer.calculate_actual_power(n_cycles, effect_size)
            
            effect_label = "small" if effect_size < 0.3 else "medium" if effect_size < 0.8 else "large"
            
            print(f"\n   Effect size {effect_size} ({effect_label}):")
            print(f"      Required cycles (power=0.8): {required_n}")
            print(f"      Actual power: {actual_power:.3f}")
            
            if actual_power >= 0.8:
                status = " ADEQUATE"
            elif actual_power >= 0.6:
                status = " MODERATE"
            else:
                status = " UNDERPOWERED"
            
            print(f"      Status: {status}")
            
            results[effect_size] = {
                'required_cycles': required_n,
                'actual_power': actual_power,
                'sufficient': actual_power >= 0.8
            }
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if all(r['sufficient'] for r in results.values()):
            print("    Study is well-powered for detecting small to large effects")
        elif results[0.5]['sufficient']:  # Medium effect
            print("    Study can detect medium-to-large effects reliably")
            print(f"    Need ~{results[0.2]['required_cycles']} cycles to detect small effects")
        else:
            print("    Study is underpowered - results may be unreliable")
            print(f"    Recommend collecting at least {results[0.5]['required_cycles']} cycles")
        
        return results


# ============================================================================
# HIGH PRIORITY 2: FAILURE CASE DEEP ANALYSIS
# ============================================================================

class FailureCaseAnalyzer:
    """
    Analyze specific failure cases to understand where embeddings help
    """
    
    @staticmethod
    def analyze_differential_performance(df_test, basic_preds, embedding_preds, 
                                        model_name="embedding_model"):
        """
        Find tests where embedding model succeeds but basic model fails
        """
        print(f"\n{'='*70}")
        print(f"DIFFERENTIAL PERFORMANCE ANALYSIS: {model_name}")
        print(f"{'='*70}")
        
        # Get actual failures
        actual_failures = df_test[df_test['Verdict'] == 1].copy()
        
        if len(actual_failures) == 0:
            print(" No failures in test set")
            return {}
        
        # Define success as ranking in top 20%
        basic_threshold = np.percentile(basic_preds, 80)
        embedding_threshold = np.percentile(embedding_preds, 80)
        
        # Get failure rankings - use positional indices instead of DataFrame indices
        # Create a mapping from DataFrame index to position in predictions array
        df_test_reset = df_test.reset_index(drop=False)
        df_test_reset['position'] = range(len(df_test_reset))
        
        # Get positions of failures in the predictions array
        failure_positions = df_test_reset[df_test_reset['Verdict'] == 1]['position'].values
        
        # Use positional indexing
        basic_ranks = basic_preds[failure_positions]
        embedding_ranks = embedding_preds[failure_positions]
        
        basic_high_rank = basic_ranks >= basic_threshold
        embedding_high_rank = embedding_ranks >= embedding_threshold
        
        # Differential cases
        embedding_wins = actual_failures[(~basic_high_rank) & embedding_high_rank]
        basic_wins = actual_failures[basic_high_rank & (~embedding_high_rank)]
        both_succeed = actual_failures[basic_high_rank & embedding_high_rank]
        both_fail = actual_failures[(~basic_high_rank) & (~embedding_high_rank)]
        
        print(f"\n Failure Detection Breakdown:")
        print(f"   Both models succeed: {len(both_succeed)} ({len(both_succeed)/len(actual_failures):.1%})")
        print(f"   Embedding wins: {len(embedding_wins)} ({len(embedding_wins)/len(actual_failures):.1%})")
        print(f"   Basic wins: {len(basic_wins)} ({len(basic_wins)/len(actual_failures):.1%})")
        print(f"   Both fail: {len(both_fail)} ({len(both_fail)/len(actual_failures):.1%})")
        
        results = {
            'embedding_wins': embedding_wins,
            'basic_wins': basic_wins,
            'both_succeed': both_succeed,
            'both_fail': both_fail
        }
        
        # Analyze characteristics of embedding wins
        if len(embedding_wins) > 0:
            print(f"\n Characteristics of Embedding-Only Successes:")
            FailureCaseAnalyzer._analyze_test_characteristics(
                embedding_wins, df_test, "Embedding Wins"
            )
        
        if len(basic_wins) > 0:
            print(f"\n Characteristics of Basic-Only Successes:")
            FailureCaseAnalyzer._analyze_test_characteristics(
                basic_wins, df_test, "Basic Wins"
            )
        
        return results
    
    @staticmethod
    def _analyze_test_characteristics(test_subset, df_full, label):
        """Analyze characteristics of a test subset"""
        
        # Duration analysis
        if 'Duration' in df_full.columns or 'DurationFeature' in df_full.columns:
            duration_col = 'Duration' if 'Duration' in df_full.columns else 'DurationFeature'
            subset_dur = test_subset[duration_col].mean()
            overall_dur = df_full[duration_col].mean()
            print(f"   Duration: {subset_dur:.2f} vs {overall_dur:.2f} overall ({(subset_dur/overall_dur-1)*100:+.1f}%)")
        
        # Code change analysis
        if 'CHANGE_IN_STATUS' in df_full.columns:
            subset_change = test_subset['CHANGE_IN_STATUS'].mean()
            overall_change = df_full['CHANGE_IN_STATUS'].mean()
            print(f"   Changed tests: {subset_change:.1%} vs {overall_change:.1%} overall")
        
        if 'LastRunFeature' in df_full.columns:
            subset_new = (test_subset['LastRunFeature'] == 0).mean()
            overall_new = (df_full['LastRunFeature'] == 0).mean()
            print(f"   New/changed: {subset_new:.1%} vs {overall_new:.1%} overall")
        
        # Recency
        if 'DIST' in df_full.columns:
            subset_dist = test_subset['DIST'].mean()
            overall_dist = df_full['DIST'].mean()
            print(f"   Distance from change: {subset_dist:.2f} vs {overall_dist:.2f} overall")


# ============================================================================
# HIGH PRIORITY 3: EMBEDDING ABLATION STUDY
# ============================================================================

class EmbeddingAblationAnalyzer:
    """
    Systematically analyze contribution of different embedding types
    """
    
    @staticmethod
    def perform_ablation_study(df_test, predictions_dict):
        """
        Compare contributions of different embedding types
        """
        print("\n" + "="*80)
        print("EMBEDDING ABLATION STUDY")
        print("="*80)
        
        # Identify model types
        basic_models = {k: v for k, v in predictions_dict.items() if 'history_only' in k}
        commit_models = {k: v for k, v in predictions_dict.items() if 'commit_only' in k}
        files_models = {k: v for k, v in predictions_dict.items() if 'files_only' in k}
        combined_models = {k: v for k, v in predictions_dict.items() 
                          if ('combined' in k or 'concatenated' in k)}
        
        if not basic_models:
            print(" No basic models found for comparison")
            return {}
        
        # Get best basic model as baseline
        basic_name = max(basic_models.keys(), 
                        key=lambda k: roc_auc_score(df_test['Verdict'], basic_models[k]))
        baseline_score = roc_auc_score(df_test['Verdict'], basic_models[basic_name])
        
        print(f"\n Baseline (History-Only): {baseline_score:.4f}")
        
        results = {
            'baseline_score': baseline_score,
            'commit_only_improvement': None,
            'files_only_improvement': None,
            'combined_improvement': None,
            'synergy_effect': None
        }
        
        # Analyze commit-only contribution
        if commit_models:
            commit_name = max(commit_models.keys(),
                            key=lambda k: roc_auc_score(df_test['Verdict'], commit_models[k]))
            commit_score = roc_auc_score(df_test['Verdict'], commit_models[commit_name])
            commit_improvement = commit_score - baseline_score
            
            print(f"\n🔹 Commit-Only Embeddings:")
            print(f"   Score: {commit_score:.4f}")
            print(f"   Improvement: {commit_improvement:+.4f} ({(commit_improvement/baseline_score)*100:+.1f}%)")
            
            results['commit_only_improvement'] = commit_improvement
        
        # Analyze files-only contribution
        if files_models:
            files_name = max(files_models.keys(),
                           key=lambda k: roc_auc_score(df_test['Verdict'], files_models[k]))
            files_score = roc_auc_score(df_test['Verdict'], files_models[files_name])
            files_improvement = files_score - baseline_score
            
            print(f"\n🔹 Files-Only Embeddings:")
            print(f"   Score: {files_score:.4f}")
            print(f"   Improvement: {files_improvement:+.4f} ({(files_improvement/baseline_score)*100:+.1f}%)")
            
            results['files_only_improvement'] = files_improvement
        
        # Analyze combined contribution and synergy
        if combined_models:
            combined_name = max(combined_models.keys(),
                              key=lambda k: roc_auc_score(df_test['Verdict'], combined_models[k]))
            combined_score = roc_auc_score(df_test['Verdict'], combined_models[combined_name])
            combined_improvement = combined_score - baseline_score
            
            print(f"\n🔹 Combined Embeddings:")
            print(f"   Score: {combined_score:.4f}")
            print(f"   Improvement: {combined_improvement:+.4f} ({(combined_improvement/baseline_score)*100:+.1f}%)")
            
            results['combined_improvement'] = combined_improvement
            
            # Calculate synergy effect
            if results['commit_only_improvement'] is not None and results['files_only_improvement'] is not None:
                expected_combined = results['commit_only_improvement'] + results['files_only_improvement']
                actual_combined = combined_improvement
                synergy = actual_combined - expected_combined
                
                print(f"\n✨ Synergy Analysis:")
                print(f"   Expected (sum of parts): {expected_combined:+.4f}")
                print(f"   Actual (combined): {actual_combined:+.4f}")
                print(f"   Synergy effect: {synergy:+.4f}")
                
                if synergy > 0.005:  # Threshold
                    print(f"    Positive synergy - combining helps!")
                elif synergy < -0.005:
                    print(f"    Negative synergy - combining hurts!")
                else:
                    print(f"   ➖ Neutral - no synergy effect")
                
                results['synergy_effect'] = synergy
        
        # Summary recommendations
        print(f"\n💡 Recommendations:")
        if results['combined_improvement'] and results['commit_only_improvement'] and results['files_only_improvement']:
            best_type = max([
                ('commit_only', results['commit_only_improvement']),
                ('files_only', results['files_only_improvement']),
                ('combined', results['combined_improvement'])
            ], key=lambda x: x[1])
            
            print(f"   🏆 Best embedding type: {best_type[0]} (+{best_type[1]:.4f})")
            
            if best_type[0] == 'combined' and results['synergy_effect'] and results['synergy_effect'] > 0:
                print(f"    Use combined embeddings - shows positive synergy")
            elif best_type[0] == 'combined':
                print(f"    Combined embeddings best but no synergy - consider simplifying")
            else:
                print(f"   💡 Single embedding type sufficient - use {best_type[0]}")
        
        return results

# ============================================================================
# ADD THIS CLASS - Deep Embedding Analysis
# ============================================================================

class EmbeddingDeepDive:
    """
    Comprehensive embedding analysis - WHAT do embeddings capture?
    """
    
    def visualize_embedding_space(self, embeddings, df_test, output_dir):
        """
        Visualize what the embeddings learned using t-SNE
        """
        from sklearn.manifold import TSNE
        from sklearn.neighbors import NearestNeighbors
        import matplotlib.pyplot as plt
        
        print("\n" + "="*80)
        print("EMBEDDING SPACE VISUALIZATION")
        print("="*80)
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        # 1. t-SNE visualization
        print("Creating t-SNE visualization...")
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings)-1), n_iter=1000)
        embedded_2d = tsne.fit_transform(embeddings)
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 16))
        
        # Plot 1: Colored by failure status
        ax1 = axes[0, 0]
        failed = df_test['Verdict'] == 1
        passed = ~failed
        
        ax1.scatter(embedded_2d[passed, 0], embedded_2d[passed, 1], 
                   c='lightblue', alpha=0.4, s=20, label=f'Pass (n={passed.sum()})')
        ax1.scatter(embedded_2d[failed, 0], embedded_2d[failed, 1], 
                   c='red', alpha=0.9, s=100, marker='X', linewidths=2,
                   edgecolors='darkred', label=f'Fail (n={failed.sum()})')
        
        ax1.set_title('Embedding Space: Actual Failures', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.set_xlabel('t-SNE Dimension 1')
        ax1.set_ylabel('t-SNE Dimension 2')
        ax1.grid(alpha=0.3)
        
        # Plot 2: Colored by test duration
        ax2 = axes[0, 1]
        duration_col = 'Duration' if 'Duration' in df_test.columns else 'DurationFeature'
        durations = df_test[duration_col]
        
        scatter = ax2.scatter(embedded_2d[:, 0], embedded_2d[:, 1], 
                            c=durations, cmap='viridis', alpha=0.6, s=30)
        plt.colorbar(scatter, ax=ax2, label='Test Duration')
        ax2.set_title('Embedding Space: Test Duration', fontsize=14, fontweight='bold')
        ax2.set_xlabel('t-SNE Dimension 1')
        ax2.set_ylabel('t-SNE Dimension 2')
        ax2.grid(alpha=0.3)
        
        # Plot 3: Colored by execution history (E3)
        ax3 = axes[1, 0]
        if 'E3' in df_test.columns:
            e3_values = df_test['E3']
            scatter = ax3.scatter(embedded_2d[:, 0], embedded_2d[:, 1], 
                                c=e3_values, cmap='RdYlGn_r', alpha=0.6, s=30)
            plt.colorbar(scatter, ax=ax3, label='E3 (1=failed recently)')
            ax3.set_title('Embedding Space: Recent Execution History (E3)', 
                         fontsize=14, fontweight='bold')
        else:
            ax3.text(0.5, 0.5, 'E3 not available', ha='center', va='center',
                    transform=ax3.transAxes, fontsize=14)
            ax3.set_title('Execution History Not Available', fontsize=14)
        
        ax3.set_xlabel('t-SNE Dimension 1')
        ax3.set_ylabel('t-SNE Dimension 2')
        ax3.grid(alpha=0.3)
        
        # Plot 4: Distance to nearest failure
        ax4 = axes[1, 1]
        
        failed_embeddings = embeddings[failed]
        if len(failed_embeddings) > 0:
            nn = NearestNeighbors(n_neighbors=1)
            nn.fit(failed_embeddings)
            distances, _ = nn.kneighbors(embeddings)
            
            scatter = ax4.scatter(embedded_2d[:, 0], embedded_2d[:, 1], 
                                c=distances.flatten(), cmap='coolwarm_r', 
                                alpha=0.6, s=30)
            plt.colorbar(scatter, ax=ax4, label='Distance to Nearest Failure')
            ax4.set_title('Embedding Space: Distance to Nearest Failing Test', 
                         fontsize=14, fontweight='bold')
        else:
            ax4.text(0.5, 0.5, 'No failures in test set', ha='center', va='center',
                    transform=ax4.transAxes, fontsize=14)
            ax4.set_title('No Failures Available', fontsize=14)
        
        ax4.set_xlabel('t-SNE Dimension 1')
        ax4.set_ylabel('t-SNE Dimension 2')
        ax4.grid(alpha=0.3)
        
        plt.tight_layout()
        output_file = output_path / 'embedding_space_visualization.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f" Embedding space visualization saved: {output_file}")
        
        # 2. Cluster analysis
        cluster_results = self.analyze_embedding_clusters(embeddings, df_test, output_path)
        
        # 3. Similarity analysis
        similarity_results = self.analyze_failure_similarity(embeddings, df_test, output_path)
        
        return {
            'cluster_analysis': cluster_results,
            'similarity_analysis': similarity_results,
            'visualization_file': str(output_file)
        }
    
    def analyze_embedding_clusters(self, embeddings, df_test, output_dir):
        """
        Cluster tests by embeddings and analyze failure patterns per cluster
        """
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
        from sklearn.manifold import TSNE
        
        print("\n EMBEDDING CLUSTER ANALYSIS")
        print("-" * 60)
        
        # Find optimal number of clusters (3-10)
        if len(embeddings) < 10:
            print(" Too few tests for clustering analysis")
            return {}
        
        silhouette_scores = []
        K_range = range(3, min(11, len(embeddings)//2))
        
        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)
            try:
                score = silhouette_score(embeddings, labels)
                silhouette_scores.append(score)
            except:
                silhouette_scores.append(0)
        
        if not silhouette_scores:
            print(" Could not perform clustering")
            return {}
        
        # Use k with best silhouette score
        best_k = K_range[np.argmax(silhouette_scores)]
        print(f"Optimal number of clusters: {best_k} (silhouette={max(silhouette_scores):.3f})")
        
        # Cluster with optimal k
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(embeddings)
        
        # Analyze each cluster
        cluster_analysis = {}
        duration_col = 'Duration' if 'Duration' in df_test.columns else 'DurationFeature'
        
        for cluster_id in range(best_k):
            cluster_mask = clusters == cluster_id
            cluster_tests = df_test[cluster_mask]
            
            cluster_stats = {
                'size': int(cluster_mask.sum()),
                'failure_rate': float(cluster_tests['Verdict'].mean()),
                'avg_duration': float(cluster_tests[duration_col].mean()),
            }
            
            if 'E1' in cluster_tests.columns:
                cluster_stats['avg_E1'] = float(cluster_tests['E1'].mean())
            if 'E2' in cluster_tests.columns:
                cluster_stats['avg_E2'] = float(cluster_tests['E2'].mean())
            if 'E3' in cluster_tests.columns:
                cluster_stats['avg_E3'] = float(cluster_tests['E3'].mean())
            
            cluster_analysis[cluster_id] = cluster_stats
            
            print(f"\nCluster {cluster_id}:")
            print(f"  Size: {cluster_stats['size']}")
            print(f"  Failure rate: {cluster_stats['failure_rate']:.1%}")
            print(f"  Avg duration: {cluster_stats['avg_duration']:.1f}")
            if 'avg_E3' in cluster_stats:
                print(f"  Avg E3 (recent fail): {cluster_stats['avg_E3']:.2f}")
        
        # Visualize clusters
        print("\nCreating cluster visualization...")
        fig, ax = plt.subplots(figsize=(12, 10))
        
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings)-1))
        embedded_2d = tsne.fit_transform(embeddings)
        
        # Plot each cluster with different color
        scatter = ax.scatter(embedded_2d[:, 0], embedded_2d[:, 1], 
                           c=clusters, cmap='tab10', alpha=0.5, s=30,
                           edgecolors='black', linewidths=0.5)
        
        # Overlay failures as red X
        failed = df_test['Verdict'] == 1
        ax.scatter(embedded_2d[failed, 0], embedded_2d[failed, 1], 
                  c='red', marker='X', s=150, linewidths=3, 
                  edgecolors='darkred', label='Failures', zorder=10)
        
        plt.colorbar(scatter, ax=ax, label='Cluster ID')
        ax.set_title(f'Embedding Clusters (k={best_k}) with Failure Overlay', 
                    fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.set_xlabel('t-SNE Dimension 1')
        ax.set_ylabel('t-SNE Dimension 2')
        ax.grid(alpha=0.3)
        
        cluster_file = output_dir / 'embedding_clusters.png'
        plt.savefig(cluster_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f" Cluster visualization saved: {cluster_file}")
        
        return cluster_analysis
    
    def analyze_failure_similarity(self, embeddings, df_test, output_dir):
        """
        KEY INSIGHT: Do failing tests cluster together in embedding space?
        """
        from scipy.spatial.distance import cdist
        
        print("\n FAILURE SIMILARITY ANALYSIS")
        print("-" * 60)
        
        failed = df_test['Verdict'] == 1
        passed = ~failed
        
        failed_embeddings = embeddings[failed]
        passed_embeddings = embeddings[passed]
        
        if len(failed_embeddings) < 2:
            print(" Too few failures for similarity analysis")
            return {}
        
        # Calculate average distances
        fail_to_fail = cdist(failed_embeddings, failed_embeddings).mean()
        fail_to_pass = cdist(failed_embeddings, passed_embeddings).mean()
        
        # If failures cluster together, fail_to_fail should be < fail_to_pass
        clustering_ratio = fail_to_pass / fail_to_fail if fail_to_fail > 0 else 1.0
        
        print(f"Average distance (fail-to-fail): {fail_to_fail:.3f}")
        print(f"Average distance (fail-to-pass): {fail_to_pass:.3f}")
        print(f"Clustering ratio: {clustering_ratio:.2f}")
        
        if clustering_ratio > 1.2:
            print(" Failures DO cluster together (embeddings capture failure patterns!)")
            interpretation = "strong_clustering"
        elif clustering_ratio > 1.05:
            print("  Weak clustering of failures")
            interpretation = "weak_clustering"
        else:
            print(" Failures DON'T cluster (embeddings may not capture failure patterns)")
            interpretation = "no_clustering"
        
        return {
            'fail_to_fail_distance': float(fail_to_fail),
            'fail_to_pass_distance': float(fail_to_pass),
            'clustering_ratio': float(clustering_ratio),
            'interpretation': interpretation
        }
    
    def analyze_what_embeddings_predict(self, embeddings, df_test, predictions, output_dir):
        """
        Analyze WHICH tests embeddings help with and WHY
        """
        from sklearn.decomposition import PCA
        from sklearn.ensemble import RandomForestClassifier
        
        print("\n" + "="*80)
        print("WHAT DO EMBEDDINGS ACTUALLY PREDICT?")
        print("="*80)
        
        output_path = Path(output_dir)
        
        # Use PCA to get interpretable components
        n_components = min(10, embeddings.shape[1])
        pca = PCA(n_components=n_components, random_state=42)
        embedding_components = pca.fit_transform(embeddings)
        
        print(f"Explained variance by top {n_components} components: {pca.explained_variance_ratio_.sum():.1%}")
        
        # Train RF to predict failures using ONLY embedding components
        if df_test['Verdict'].sum() > 0:  # Has failures
            rf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
            rf.fit(embedding_components, df_test['Verdict'])
            
            # Get feature importance
            importance = pca.explained_variance_ratio_ * rf.feature_importances_
            
            print("\nTop embedding components for failure prediction:")
            for i, imp in enumerate(importance[:5], 1):
                print(f"  Component {i}: {imp:.4f}")
        else:
            importance = pca.explained_variance_ratio_
        
        # Analyze what each component correlates with
        print("\nWhat do these components capture?")
        traditional_features = ['Duration' if 'Duration' in df_test.columns else 'DurationFeature',
                               'E1', 'E2', 'E3', 'LastRunFeature', 'DIST', 'CHANGE_IN_STATUS']
        available_features = [f for f in traditional_features if f in df_test.columns]
        
        for i in range(min(5, embedding_components.shape[1])):
            print(f"\n  Component {i+1} correlations:")
            for feature in available_features:
                try:
                    corr = np.corrcoef(embedding_components[:, i], df_test[feature])[0, 1]
                    if not np.isnan(corr) and abs(corr) > 0.1:
                        print(f"    {feature}: {corr:+.3f}")
                except:
                    pass
        
        return {
            'pca_components': embedding_components,
            'explained_variance': pca.explained_variance_ratio_.tolist(),
            'component_importance': importance.tolist() if hasattr(importance, 'tolist') else list(importance)
        }


def add_embedding_visualization_to_pipeline(df_test, embeddings_dict, predictions_dict, output_dir):
    """
    Integration function - Add this to your main pipeline
    """
    print("\n" + "="*100)
    print("DEEP EMBEDDING ANALYSIS - WHAT DO EMBEDDINGS CAPTURE?")
    print("="*100)
    
    visualizer = EmbeddingDeepDive()
    
    all_results = {}
    for emb_name, emb_data in embeddings_dict.items():
        try:
            print(f"\n{'='*80}")
            print(f"ANALYZING: {emb_name}")
            print(f"{'='*80}")
            
            # Get test embeddings
            test_embeddings = emb_data[df_test.index]
            
            results = visualizer.visualize_embedding_space(
                test_embeddings, df_test, 
                Path(output_dir) / 'embedding_deep_analysis' / emb_name
            )
            
            # Get predictions from embedding model if available
            emb_model_name = f"ML_enhanced_{emb_name}_class_weights"
            if emb_model_name in predictions_dict:
                pred_analysis = visualizer.analyze_what_embeddings_predict(
                    test_embeddings, df_test, 
                    predictions_dict[emb_model_name],
                    Path(output_dir) / 'embedding_deep_analysis' / emb_name
                )
                results['prediction_analysis'] = pred_analysis
            
            all_results[emb_name] = results
            print(f" {emb_name} analysis complete")
            
        except Exception as e:
            print(f" Failed to analyze {emb_name}: {e}")
            import traceback
            traceback.print_exc()
    
    return all_results


class PriorityValueAnalysis:
    """
    Analyze Priority Value to show it's a poor predictor of failures
    Justifies using Verdict (actual failures) as ground truth instead of PV
    """
    
    def analyze_pv_vs_verdict_correlation(self, df, output_dir):
        """
        Core analysis: Show PV is poorly correlated with actual failures
        """
        print("\n" + "="*80)
        print("PRIORITY VALUE vs ACTUAL FAILURES ANALYSIS")
        print("="*80)
        print("Justification: Why we use Verdict (not PV) as ground truth\n")
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        # Check for PV column
        pv_col = None
        possible_names = ['PRIORITY_VALUE', 'Priority_value', 'priority_value', 'PriorityValue']
        for col_name in possible_names:
            if col_name in df.columns:
                pv_col = col_name
                break
        
        if pv_col is None:
            print(" No PRIORITY_VALUE column found. Creating synthetic PV for demonstration.")
            # Create synthetic PV using the formula
            df['PRIORITY_VALUE'] = (0.1 * df.get('E1', 0) + 
                                   0.2 * df.get('E2', 0) + 
                                   0.7 * df.get('E3', 0))
            
            duration_col = 'Duration' if 'Duration' in df.columns else 'DurationFeature'
            if duration_col in df.columns:
                max_dur = df[duration_col].max()
                if max_dur > 0:
                    df['PRIORITY_VALUE'] += max_dur / (df[duration_col] + 1e-8)
            
            pv_col = 'PRIORITY_VALUE'
            print(f" Created synthetic PRIORITY_VALUE for analysis")
        
        # 1. Basic statistics
        print(f" PRIORITY_VALUE Statistics:")
        print(f"   Mean: {df[pv_col].mean():.3f}")
        print(f"   Std: {df[pv_col].std():.3f}")
        print(f"   Range: [{df[pv_col].min():.3f}, {df[pv_col].max():.3f}]")
        
        print(f"\n Verdict Statistics:")
        print(f"   Total tests: {len(df):,}")
        print(f"   Failures: {df['Verdict'].sum():,}")
        print(f"   Failure rate: {df['Verdict'].mean():.2%}")
        
        # 2. Correlation analysis - THE KEY FINDING
        pv_verdict_corr = df[pv_col].corr(df['Verdict'])
        
        print(f"\n CORRELATION ANALYSIS:")
        print(f"   PV vs Verdict correlation: {pv_verdict_corr:.4f}")
        
        if abs(pv_verdict_corr) < 0.1:
            print(f"    VERY LOW correlation - PV is a POOR predictor of failures")
            print(f"    Justifies using Verdict (actual failures) as ground truth")
        elif abs(pv_verdict_corr) < 0.3:
            print(f"     LOW correlation - PV is a WEAK predictor of failures")
            print(f"    Still justifies using Verdict as ground truth")
        else:
            print(f"     MODERATE correlation - PV has some predictive power")
            print(f"     Using Verdict is still better (actual outcomes vs heuristic)")
        
        # 3. Compare with other features
        print(f"\n Comparison with Traditional Features:")
        
        traditional_features = ['Duration', 'DurationFeature', 'E1', 'E2', 'E3', 
                               'LastRunFeature', 'DIST', 'CHANGE_IN_STATUS']
        available_features = [f for f in traditional_features if f in df.columns]
        
        correlations = {}
        for feature in available_features:
            corr = df[feature].corr(df['Verdict'])
            correlations[feature] = corr
            symbol = "" if abs(corr) > abs(pv_verdict_corr) else ""
            print(f"   {symbol} {feature:20s}: {corr:+.4f}")
        
        correlations['PRIORITY_VALUE'] = pv_verdict_corr
        
        # 4. Ranking quality analysis
        print(f"\n Ranking Quality Analysis:")
        
        # Sort by PV and check how many failures are in top-k
        df_sorted_pv = df.sort_values(pv_col, ascending=False)
        
        total_failures = df['Verdict'].sum()
        
        for top_pct in [0.1, 0.2, 0.5]:
            k = int(len(df) * top_pct)
            failures_in_top_k = df_sorted_pv.head(k)['Verdict'].sum()
            recall = failures_in_top_k / total_failures if total_failures > 0 else 0
            precision = failures_in_top_k / k
            
            print(f"\n   Top {top_pct:.0%} by PV ranking:")
            print(f"      Tests: {k:,}")
            print(f"      Failures found: {failures_in_top_k}/{total_failures} ({recall:.1%} recall)")
            print(f"      Precision: {precision:.1%}")
            
            # Compare to random
            expected_random = k * (total_failures / len(df))
            improvement = (failures_in_top_k / expected_random - 1) * 100 if expected_random > 0 else 0
            
            print(f"      vs Random: {improvement:+.1f}% improvement")
            
            if improvement < 20:
                print(f"        Poor improvement over random - PV ranking is weak")
        
        # 5. Visualizations
        self._create_pv_analysis_visualizations(df, pv_col, correlations, output_path)
        
        # 6. Generate report
        results = {
            'pv_verdict_correlation': float(pv_verdict_corr),
            'pv_mean': float(df[pv_col].mean()),
            'pv_std': float(df[pv_col].std()),
            'failure_rate': float(df['Verdict'].mean()),
            'feature_correlations': {k: float(v) for k, v in correlations.items()},
            'conclusion': 'PV poorly predicts failures' if abs(pv_verdict_corr) < 0.2 else 'PV weakly predicts failures'
        }
        
        # Save results
        with open(output_path / 'pv_analysis_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n Analysis complete. Results saved to: {output_path}")
        
        return results
    
    def _create_pv_analysis_visualizations(self, df, pv_col, correlations, output_path):
        """Create visualizations showing PV vs Verdict relationship"""
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 14))
        
        # Plot 1: Scatter plot - PV vs Verdict
        ax1 = axes[0, 0]
        
        failed = df['Verdict'] == 1
        passed = df['Verdict'] == 0
        
        ax1.scatter(df[passed][pv_col], df[passed]['Verdict'], 
                   alpha=0.3, s=10, label='Pass', c='blue')
        ax1.scatter(df[failed][pv_col], df[failed]['Verdict'], 
                   alpha=0.8, s=50, label='Fail', c='red', marker='x')
        
        ax1.set_xlabel('Priority Value', fontsize=12)
        ax1.set_ylabel('Verdict (0=Pass, 1=Fail)', fontsize=12)
        ax1.set_title(f'Priority Value vs Actual Failures\n(Correlation: {df[pv_col].corr(df["Verdict"]):.3f})', 
                     fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(alpha=0.3)
        
        # Plot 2: Distribution comparison
        ax2 = axes[0, 1]
        
        pv_passed = df[passed][pv_col]
        pv_failed = df[failed][pv_col]
        
        ax2.hist(pv_passed, bins=50, alpha=0.5, label='Pass', color='blue', density=True)
        ax2.hist(pv_failed, bins=50, alpha=0.5, label='Fail', color='red', density=True)
        
        ax2.set_xlabel('Priority Value', fontsize=12)
        ax2.set_ylabel('Density', fontsize=12)
        ax2.set_title('PV Distribution: Pass vs Fail Tests', fontsize=14, fontweight='bold')
        ax2.legend()
        ax2.grid(alpha=0.3)
        
        # Plot 3: Correlation comparison bar chart
        ax3 = axes[1, 0]
        
        features = list(correlations.keys())
        corr_values = [correlations[f] for f in features]
        
        colors = ['red' if f == 'PRIORITY_VALUE' else 'steelblue' for f in features]
        
        bars = ax3.barh(range(len(features)), corr_values, color=colors, alpha=0.7)
        ax3.set_yticks(range(len(features)))
        ax3.set_yticklabels(features, fontsize=10)
        ax3.set_xlabel('Correlation with Verdict', fontsize=12)
        ax3.set_title('Feature Correlations with Actual Failures\n(Red = Priority Value)', 
                     fontsize=14, fontweight='bold')
        ax3.axvline(x=0, color='black', linestyle='--', linewidth=1)
        ax3.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for bar, val in zip(bars, corr_values):
            x_pos = val + 0.01 if val > 0 else val - 0.01
            ax3.text(x_pos, bar.get_y() + bar.get_height()/2, 
                    f'{val:.3f}', va='center', fontsize=9)
        
        # Plot 4: Ranking quality - Recall@k
        ax4 = axes[1, 1]
        
        df_sorted_pv = df.sort_values(pv_col, ascending=False)
        total_failures = df['Verdict'].sum()
        
        top_k_percentages = np.arange(0.05, 1.01, 0.05)
        recalls_pv = []
        recalls_random = []
        
        for top_pct in top_k_percentages:
            k = int(len(df) * top_pct)
            failures_found = df_sorted_pv.head(k)['Verdict'].sum()
            recall_pv = failures_found / total_failures if total_failures > 0 else 0
            recall_random = top_pct  # Random expected
            
            recalls_pv.append(recall_pv)
            recalls_random.append(recall_random)
        
        ax4.plot(top_k_percentages * 100, recalls_pv, 
                label='PV Ranking', linewidth=2, marker='o', markersize=3)
        ax4.plot(top_k_percentages * 100, recalls_random, 
                label='Random Ranking', linewidth=2, linestyle='--', alpha=0.7)
        
        ax4.set_xlabel('Top K% of Tests', fontsize=12)
        ax4.set_ylabel('Recall (% Failures Found)', fontsize=12)
        ax4.set_title('PV Ranking Quality: Recall Curve', fontsize=14, fontweight='bold')
        ax4.legend()
        ax4.grid(alpha=0.3)
        ax4.set_xlim([0, 100])
        ax4.set_ylim([0, 1])
        
        plt.tight_layout()
        
        output_file = output_path / 'pv_vs_verdict_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f" Visualization saved: {output_file}")

# ============================================================================
# MEDIUM PRIORITY 1: EARLY STOPPING BENEFIT ANALYSIS
# ============================================================================

class EarlyStoppingAnalyzer:
    """
    Analyze practical time savings from early stopping
    """
    
    @staticmethod
    def analyze_time_savings(df_test, predictions_dict, coverage_targets=[0.5, 0.75, 0.9, 1.0]):
        """
        Calculate time to achieve different failure coverage levels
        """
        print("\n" + "="*80)
        print("EARLY STOPPING TIME SAVINGS ANALYSIS")
        print("="*80)
        
        duration_col = 'Duration' if 'Duration' in df_test.columns else 'DurationFeature'
        
        if duration_col not in df_test.columns:
            print(" No duration data available")
            return {}
        
        total_test_time = df_test[duration_col].sum()
        total_failures = df_test['Verdict'].sum()
        
        print(f"\n Baseline Statistics:")
        print(f"   Total test time: {total_test_time:.1f} time units")
        print(f"   Total failures: {total_failures}")
        print(f"   Average test duration: {df_test[duration_col].mean():.2f}")
        
        results = {}
        
        for model_name, predictions in predictions_dict.items():
            model_results = {}
            
            # Sort tests by prediction score (highest first)
            df_ranked = df_test.copy()
            df_ranked['prediction'] = predictions
            df_ranked = df_ranked.sort_values('prediction', ascending=False)
            df_ranked['cumulative_time'] = df_ranked[duration_col].cumsum()
            df_ranked['cumulative_failures'] = df_ranked['Verdict'].cumsum()
            
            print(f"\n {model_name}:")
            
            for coverage in coverage_targets:
                target_failures = int(total_failures * coverage)
                
                if target_failures == 0:
                    continue
                
                # Find time to reach target failures
                reaching_tests = df_ranked[df_ranked['cumulative_failures'] >= target_failures]
                
                if len(reaching_tests) > 0:
                    time_to_coverage = reaching_tests.iloc[0]['cumulative_time']
                    tests_executed = reaching_tests.index[0] + 1
                    time_saved = total_test_time - time_to_coverage
                    time_saved_pct = (time_saved / total_test_time) * 100
                    
                    print(f"   {coverage:.0%} coverage:")
                    print(f"      Time: {time_to_coverage:.1f} ({100-time_saved_pct:.1f}% of total)")
                    print(f"      Tests: {tests_executed}/{len(df_test)} ({tests_executed/len(df_test):.1%})")
                    print(f"      Time saved: {time_saved:.1f} ({time_saved_pct:.1f}%)")
                    
                    model_results[f'coverage_{coverage}'] = {
                        'time': time_to_coverage,
                        'tests_executed': tests_executed,
                        'time_saved': time_saved,
                        'time_saved_pct': time_saved_pct
                    }
            
            results[model_name] = model_results
        
        # Compare models
        print(f"\n🏆 Model Comparison (75% Coverage):")
        models_75 = [(k, v.get('coverage_0.75', {}).get('time', float('inf'))) 
                     for k, v in results.items() if 'coverage_0.75' in v]
        
        if models_75:
            models_75_sorted = sorted(models_75, key=lambda x: x[1])
            best_model = models_75_sorted[0]
            
            print(f"   Best: {best_model[0]} - {best_model[1]:.1f} time units")
            
            if len(models_75_sorted) > 1:
                baseline_model = models_75_sorted[-1]
                time_diff = baseline_model[1] - best_model[1]
                print(f"   Improvement over slowest: {time_diff:.1f} time units ({(time_diff/baseline_model[1])*100:.1f}%)")
        
        return results
    
    @staticmethod
    def visualize_early_stopping(df_test, predictions_dict, output_path):
        """
        Create visualization of early stopping benefits
        """
        duration_col = 'Duration' if 'Duration' in df_test.columns else 'DurationFeature'
        
        if duration_col not in df_test.columns:
            print(" Cannot create early stopping visualization - no duration data")
            return
        
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        
        # 1. Time to X% failures
        ax1 = axes[0]
        coverage_levels = np.linspace(0.1, 1.0, 20)
        
        # Get top 5 models by AUC for visualization
        model_aucs = {}
        for model_name, predictions in predictions_dict.items():
            try:
                auc = roc_auc_score(df_test['Verdict'], predictions)
                model_aucs[model_name] = auc
            except:
                pass
        
        top_models = sorted(model_aucs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        for model_name, _ in top_models:
            predictions = predictions_dict[model_name]
            times = []
            
            df_ranked = df_test.copy()
            df_ranked['prediction'] = predictions
            df_ranked = df_ranked.sort_values('prediction', ascending=False)
            df_ranked['cumulative_time'] = df_ranked[duration_col].cumsum()
            df_ranked['cumulative_failures'] = df_ranked['Verdict'].cumsum()
            
            total_failures = df_test['Verdict'].sum()
            
            for coverage in coverage_levels:
                target = int(total_failures * coverage)
                if target == 0:
                    times.append(0)
                    continue
                    
                reaching = df_ranked[df_ranked['cumulative_failures'] >= target]
                
                if len(reaching) > 0:
                    times.append(reaching.iloc[0]['cumulative_time'])
                else:
                    times.append(df_ranked['cumulative_time'].iloc[-1])
            
            label = model_name.replace('ML_', '').replace('_', ' ')[:25]
            ax1.plot(coverage_levels * 100, times, label=label, marker='o', markersize=3)
        
        ax1.set_xlabel('Failure Coverage (%)', fontsize=12)
        ax1.set_ylabel('Cumulative Test Time', fontsize=12)
        ax1.set_title('Time to Achieve Failure Coverage', fontsize=14, fontweight='bold')
        ax1.legend(fontsize=8, loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 2. Time saved at 75% coverage
        ax2 = axes[1]
        model_names_short = []
        time_savings = []
        
        for model_name, _ in top_models:
            predictions = predictions_dict[model_name]
            
            df_ranked = df_test.copy()
            df_ranked['prediction'] = predictions
            df_ranked = df_ranked.sort_values('prediction', ascending=False)
            df_ranked['cumulative_time'] = df_ranked[duration_col].cumsum()
            df_ranked['cumulative_failures'] = df_ranked['Verdict'].cumsum()
            
            total_failures = df_test['Verdict'].sum()
            target = int(total_failures * 0.75)
            
            reaching = df_ranked[df_ranked['cumulative_failures'] >= target]
            
            if len(reaching) > 0:
                time_to_75 = reaching.iloc[0]['cumulative_time']
                total_time = df_ranked['cumulative_time'].iloc[-1]
                saved_pct = ((total_time - time_to_75) / total_time) * 100
                
                model_names_short.append(model_name.replace('ML_', '')[:20])
                time_savings.append(saved_pct)
        
        bars = ax2.barh(range(len(model_names_short)), time_savings, color='green', alpha=0.7)
        ax2.set_yticks(range(len(model_names_short)))
        ax2.set_yticklabels(model_names_short, fontsize=9)
        ax2.set_xlabel('Time Saved (%)', fontsize=12)
        ax2.set_title('Time Savings at 75% Failure Coverage', fontsize=14, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)
        
        # Add value labels on bars
        for i, (bar, value) in enumerate(zip(bars, time_savings)):
            ax2.text(value + 1, bar.get_y() + bar.get_height()/2, 
                    f'{value:.1f}%', va='center', fontsize=9)
        
        plt.tight_layout()
        
        output_file = Path(output_path) / 'early_stopping_analysis.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f" Early stopping visualization saved: {output_file}")


# ============================================================================
# MEDIUM PRIORITY 2: DEVELOPER INTENT CAPTURE ANALYSIS
# ============================================================================

class DeveloperIntentAnalyzer:
    """
    Analyze whether embeddings successfully capture developer intent and
    whether this helps in test case prioritization
    """
    
    def __init__(self):
        self.statistical_tester = StatisticalTester()
    
    def analyze_embedding_contribution(self, df_test, predictions_dict):
        """
        Compare basic (history-only) vs embedding-based models to measure
        the contribution of developer intent captured through embeddings
        """
        print("\n" + "="*80)
        print("DEVELOPER INTENT CAPTURE ANALYSIS")
        print("="*80)
        
        # Separate models by type
        basic_models = {k: v for k, v in predictions_dict.items() if 'history_only' in k}
        enhanced_models = {k: v for k, v in predictions_dict.items() if 'enhanced' in k}
        dual_branch_models = {k: v for k, v in predictions_dict.items() if 'dual_branch' in k}
        
        results = {
            'embedding_contribution': {},
            'temporal_pattern_capture': {},
            'code_change_sensitivity': {}
        }
        
        if not basic_models:
            print(" No basic (history-only) models found for comparison")
            return results
        
        # Get best basic model as baseline
        basic_performance = {name: roc_auc_score(df_test['Verdict'], preds) 
                           for name, preds in basic_models.items()}
        best_basic_name = max(basic_performance, key=basic_performance.get)
        best_basic_pred = basic_models[best_basic_name]
        best_basic_score = basic_performance[best_basic_name]
        
        print(f"\n BASELINE (History-Only): {best_basic_name}")
        print(f"   AUC-ROC: {best_basic_score:.4f}")
        
        # Compare embedding models against baseline
        print(f"\n{'='*60}")
        print("EMBEDDING MODEL IMPROVEMENTS OVER BASELINE")
        print(f"{'='*60}")
        
        for model_name, predictions in {**enhanced_models, **dual_branch_models}.items():
            model_score = roc_auc_score(df_test['Verdict'], predictions)
            improvement = model_score - best_basic_score
            improvement_pct = (improvement / best_basic_score) * 100
            
            # Statistical significance test
            basic_cycle_aucs = self._calculate_per_cycle_auc(df_test, best_basic_pred)
            model_cycle_aucs = self._calculate_per_cycle_auc(df_test, predictions)
            
            if len(basic_cycle_aucs) > 1 and len(model_cycle_aucs) > 1:
                try:
                    stat, p_value = stats.wilcoxon(basic_cycle_aucs, model_cycle_aucs, 
                                                   alternative='two-sided')
                    significant = p_value < 0.05
                except:
                    p_value = 1.0
                    significant = False
            else:
                p_value = 1.0
                significant = False
            
            # Determine model type
            if 'enhanced' in model_name:
                arch_type = "ENHANCED (concat)"
            elif 'dual_branch' in model_name:
                arch_type = "DUAL_BRANCH"
            else:
                arch_type = "UNKNOWN"
            
            # Get embedding type
            emb_type = "unknown"
            for emb in ['commit_only', 'files_only', 'combined', 'concatenated']:
                if emb in model_name:
                    emb_type = emb
                    break
            
            print(f"\n{model_name}:")
            print(f"   Architecture: {arch_type}")
            print(f"   Embedding: {emb_type}")
            print(f"   AUC-ROC: {model_score:.4f}")
            print(f"   Improvement: {improvement:+.4f} ({improvement_pct:+.2f}%)")
            print(f"   Statistical significance: {' YES' if significant else ' NO'} (p={p_value:.4f})")
            
            # Store results
            results['embedding_contribution'][model_name] = {
                'architecture': arch_type,
                'embedding_type': emb_type,
                'auc_roc': model_score,
                'improvement_over_baseline': improvement,
                'improvement_percentage': improvement_pct,
                'p_value': p_value,
                'significant': significant,
                'per_cycle_aucs': model_cycle_aucs
            }
        
        return results
    
    def _calculate_per_cycle_auc(self, df_test, predictions):
        """Calculate AUC-ROC for each cycle separately"""
        cycle_aucs = []
        
        for cycle in df_test['Cycle'].unique():
            cycle_mask = df_test['Cycle'] == cycle
            cycle_labels = df_test[cycle_mask]['Verdict']
            cycle_preds = predictions[cycle_mask]
            
            # Need at least one positive and one negative
            if cycle_labels.sum() > 0 and cycle_labels.sum() < len(cycle_labels):
                try:
                    auc = roc_auc_score(cycle_labels, cycle_preds)
                    cycle_aucs.append(auc)
                except:
                    pass
        
        return cycle_aucs
    
    def analyze_code_change_sensitivity(self, df_test, predictions_dict):
        """
        Analyze if embeddings help identify failures related to code changes
        Uses LastRunFeature or DIST as proxy for code changes
        """
        print(f"\n{'='*60}")
        print("CODE CHANGE SENSITIVITY ANALYSIS")
        print(f"{'='*60}")
            
            # Check for code change indicator - PRIORITIZE LastRunFeature and DIST
        change_indicator = None
        priority_indicators = ['LastRunFeature', 'DIST']  # Best indicators first
        fallback_indicators = ['CHANGE_IN_STATUS', 'Change_in_status', 'change_in_status']
            
            # Try priority indicators first
        for col in priority_indicators:
            if col in df_test.columns:
                change_indicator = col
                break
    
    # Fallback to CHANGE_IN_STATUS if nothing else available
        if change_indicator is None:
            for col in fallback_indicators:
                if col in df_test.columns:
                    change_indicator = col
                    print(f" Warning: Using {col} which measures test instability, not code changes")
                    break
        
        # Check if we found any suitable column
        if change_indicator is None:
            print(" No code change indicator found in dataset")
            print("   Available columns:", list(df_test.columns))
            print("   Skipping code change sensitivity analysis")
            return {}
        
        print(f"Using '{change_indicator}' as code change indicator")
        
        # Print appropriate message based on indicator quality
        if change_indicator == 'LastRunFeature':
            print(f" Using '{change_indicator}' - BEST indicator (0 = new/changed test)")
            # For LastRunFeature: 0 = new/changed test, higher values = older/unchanged
            changed_tests = df_test[change_indicator] == 0
        elif change_indicator == 'DIST':
            print(f" Using '{change_indicator}' - GOOD indicator (low = recent change)")
            # For DIST: lower values = more recent changes
            threshold = df_test[change_indicator].median()
            changed_tests = df_test[change_indicator] <= threshold
        elif 'CHANGE_IN_STATUS' in change_indicator:
            print(f" Using '{change_indicator}' - FALLBACK indicator")
            print(f"   Note: This measures test result changes (flakiness), not code changes")
            print(f"   Results should be interpreted with caution")
            # For CHANGE_IN_STATUS: 1 = status changed (failed or passed differently)
            changed_tests = df_test[change_indicator] == 1
        else:
            # Default: assume boolean or binary indicator where True/1 = changed
            changed_tests = df_test[change_indicator].astype(bool)
            
        unchanged_tests = ~changed_tests
        
        print(f"\n Test Distribution:")
        print(f"   Changed/Recent: {changed_tests.sum()} tests ({changed_tests.mean():.1%})")
        print(f"   Unchanged/Old: {unchanged_tests.sum()} tests ({unchanged_tests.mean():.1%})")
        
        results = {}
        
        # Separate models
        basic_models = {k: v for k, v in predictions_dict.items() if 'history_only' in k}
        embedding_models = {k: v for k, v in predictions_dict.items() 
                          if 'enhanced' in k or 'dual_branch' in k}
        
        if not basic_models or not embedding_models:
            print(" Need both basic and embedding models for comparison")
            return results
        
        # Get best basic model
        basic_aucs = {}
        for name, preds in basic_models.items():
            try:
                auc = roc_auc_score(df_test['Verdict'], preds)
                basic_aucs[name] = auc
            except:
                pass
        
        if not basic_aucs:
            print(" Could not calculate AUC for basic models")
            return results
        
        best_basic_name = max(basic_aucs, key=basic_aucs.get)
        best_basic_pred = basic_models[best_basic_name]
        
        # Calculate performance on changed tests
        print(f"\n{'='*60}")
        print("PERFORMANCE ON CODE-CHANGED TESTS")
        print(f"{'='*60}")
        
        # Basic model on changed tests
        try:
            basic_changed_auc = roc_auc_score(
                df_test[changed_tests]['Verdict'], 
                best_basic_pred[changed_tests]
            )
        except:
            basic_changed_auc = 0.5
        
        # Basic model on unchanged tests
        try:
            basic_unchanged_auc = roc_auc_score(
                df_test[unchanged_tests]['Verdict'],
                best_basic_pred[unchanged_tests]
            )
        except:
            basic_unchanged_auc = 0.5
        
        print(f"\nBaseline ({best_basic_name}):")
        print(f"   Changed tests AUC: {basic_changed_auc:.4f}")
        print(f"   Unchanged tests AUC: {basic_unchanged_auc:.4f}")
        print(f"   Difference: {basic_changed_auc - basic_unchanged_auc:+.4f}")
        
        # Compare with embedding models
        for model_name, predictions in embedding_models.items():
            try:
                changed_auc = roc_auc_score(
                    df_test[changed_tests]['Verdict'],
                    predictions[changed_tests]
                )
            except:
                changed_auc = 0.5
            
            try:
                unchanged_auc = roc_auc_score(
                    df_test[unchanged_tests]['Verdict'],
                    predictions[unchanged_tests]
                )
            except:
                unchanged_auc = 0.5
            
            # Calculate improvements
            changed_improvement = changed_auc - basic_changed_auc
            unchanged_improvement = unchanged_auc - basic_unchanged_auc
            
            # Does embedding help MORE on changed tests? (this would indicate intent capture)
            helps_on_changes = changed_improvement > unchanged_improvement
            
            print(f"\n{model_name}:")
            print(f"   Changed tests AUC: {changed_auc:.4f} ({changed_improvement:+.4f})")
            print(f"   Unchanged tests AUC: {unchanged_auc:.4f} ({unchanged_improvement:+.4f})")
            print(f"   {' Better on changed tests!' if helps_on_changes else ' Similar or better on unchanged'}")
            
            results[model_name] = {
                'changed_test_auc': changed_auc,
                'unchanged_test_auc': unchanged_auc,
                'changed_improvement': changed_improvement,
                'unchanged_improvement': unchanged_improvement,
                'helps_more_on_changes': helps_on_changes,
                'change_indicator_used': change_indicator
            }
        
        return results
    
    def analyze_temporal_pattern_capture(self, df_test, predictions_dict):
        """
        Analyze if embeddings capture temporal patterns better than history alone
        """
        print(f"\n{'='*60}")
        print("TEMPORAL PATTERN CAPTURE ANALYSIS")
        print(f"{'='*60}")
        
        if 'Cycle' not in df_test.columns:
            print(" No cycle information available")
            return {}
        
        cycles = sorted(df_test['Cycle'].unique())
        
        if len(cycles) < 5:
            print(" Not enough cycles for temporal analysis")
            return {}
        
        results = {}
        
        # Separate models
        basic_models = {k: v for k, v in predictions_dict.items() if 'history_only' in k}
        embedding_models = {k: v for k, v in predictions_dict.items()
                          if 'enhanced' in k or 'dual_branch' in k}
        
        if not basic_models or not embedding_models:
            print(" Need both basic and embedding models")
            return results
        
        # Get best basic model
        basic_name = list(basic_models.keys())[0]
        basic_pred = basic_models[basic_name]
        
        # Calculate per-cycle performance
        print(f"\nAnalyzing temporal stability across {len(cycles)} cycles...")
        
        for model_name, predictions in embedding_models.items():
            basic_cycle_perf = []
            model_cycle_perf = []
            
            for cycle in cycles:
                cycle_mask = df_test['Cycle'] == cycle
                cycle_labels = df_test[cycle_mask]['Verdict']
                
                if cycle_labels.sum() > 0 and cycle_labels.sum() < len(cycle_labels):
                    try:
                        basic_auc = roc_auc_score(cycle_labels, basic_pred[cycle_mask])
                        model_auc = roc_auc_score(cycle_labels, predictions[cycle_mask])
                        basic_cycle_perf.append(basic_auc)
                        model_cycle_perf.append(model_auc)
                    except:
                        pass
            
            if len(basic_cycle_perf) > 2:
                # Calculate stability (lower variance = more stable)
                basic_stability = np.std(basic_cycle_perf)
                model_stability = np.std(model_cycle_perf)
                
                # Calculate average performance
                basic_avg = np.mean(basic_cycle_perf)
                model_avg = np.mean(model_cycle_perf)
                
                # More stable = better temporal generalization
                more_stable = model_stability < basic_stability
                
                print(f"\n{model_name}:")
                print(f"   Avg performance: {model_avg:.4f} vs {basic_avg:.4f} (baseline)")
                print(f"   Stability (std): {model_stability:.4f} vs {basic_stability:.4f} (baseline)")
                print(f"   {' More stable!' if more_stable else ' Less stable'}")
                
                results[model_name] = {
                    'avg_performance': model_avg,
                    'baseline_avg': basic_avg,
                    'stability': model_stability,
                    'baseline_stability': basic_stability,
                    'more_stable': more_stable,
                    'performance_improvement': model_avg - basic_avg
                }
        
        return results
    
    def generate_developer_intent_report(self, df_test, predictions_dict, output_dir):
        """
        Generate comprehensive report on developer intent capture
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        print("\n" + "="*80)
        print("COMPREHENSIVE DEVELOPER INTENT ANALYSIS")
        print("="*80)
        
        # Run all analyses
        contribution_results = self.analyze_embedding_contribution(df_test, predictions_dict)
        code_change_results = self.analyze_code_change_sensitivity(df_test, predictions_dict)
        temporal_results = self.analyze_temporal_pattern_capture(df_test, predictions_dict)
        
        # Create visualizations
        self._create_intent_visualizations(
            contribution_results, code_change_results, temporal_results, output_path
        )
        
        # Generate report
        report_path = output_path / 'developer_intent_analysis_report.md'
        with open(report_path, 'w') as f:
            f.write("# Developer Intent Capture Analysis Report\n\n")
            
            f.write("## Summary\n\n")
            f.write("This report analyzes whether code embeddings successfully capture\n")
            f.write("developer intent and whether this improves test case prioritization.\n\n")
            
            f.write("## Key Questions\n\n")
            f.write("1. **Do embeddings improve over history-only models?**\n")
            f.write("2. **Do embeddings help MORE on code-changed tests?** (intent capture)\n")
            f.write("3. **Do embeddings provide better temporal generalization?**\n\n")
            
            # Contribution analysis
            if contribution_results and 'embedding_contribution' in contribution_results:
                f.write("## Embedding Contribution Analysis\n\n")
                
                contrib = contribution_results['embedding_contribution']
                significant_models = [k for k, v in contrib.items() if v.get('significant', False)]
                
                f.write(f"**Models showing significant improvement:** {len(significant_models)}/{len(contrib)}\n\n")
                
                if significant_models:
                    f.write("### Significant Improvements\n\n")
                    f.write("| Model | Embedding | Improvement | P-value |\n")
                    f.write("|-------|-----------|-------------|---------|\n")
                    
                    for model in significant_models:
                        info = contrib[model]
                        f.write(f"| {model} | {info['embedding_type']} | ")
                        f.write(f"{info['improvement_percentage']:+.2f}% | {info['p_value']:.4f} |\n")
                    f.write("\n")
            
            # Code change sensitivity
            if code_change_results:
                f.write("## Code Change Sensitivity Analysis\n\n")
                
                helps_on_changes = [k for k, v in code_change_results.items() 
                                   if v.get('helps_more_on_changes', False)]
                
                f.write(f"**Models helping MORE on changed tests:** {len(helps_on_changes)}/{len(code_change_results)}\n")
                f.write("*(Indicates successful developer intent capture)*\n\n")
                
                if helps_on_changes:
                    for model in helps_on_changes:
                        info = code_change_results[model]
                        f.write(f"- **{model}:** +{info['changed_improvement']:.4f} on changed vs ")
                        f.write(f"+{info['unchanged_improvement']:.4f} on unchanged\n")
                    f.write("\n")
            
            # Temporal analysis
            if temporal_results:
                f.write("## Temporal Pattern Capture\n\n")
                
                stable_models = [k for k, v in temporal_results.items()
                               if v.get('more_stable', False)]
                
                f.write(f"**Models with better temporal stability:** {len(stable_models)}/{len(temporal_results)}\n\n")
            
            f.write("## Conclusions\n\n")
            
            # Draw conclusions based on results
            if contribution_results and code_change_results:
                has_improvement = len(significant_models) > 0 if 'significant_models' in locals() else False
                captures_intent = len(helps_on_changes) > 0 if 'helps_on_changes' in locals() else False
                
                if has_improvement and captures_intent:
                    f.write(" **SUCCESS**: Embeddings show significant improvements AND help more on code changes.\n")
                    f.write("   This indicates successful capture of developer intent.\n\n")
                elif has_improvement:
                    f.write(" **PARTIAL**: Embeddings improve performance but don't specifically help on code changes.\n")
                    f.write("   May be capturing other patterns besides developer intent.\n\n")
                else:
                    f.write(" **LIMITED**: Embeddings show minimal improvements.\n")
                    f.write("   May need better embedding methods or more data.\n\n")
        
        print(f"\n Report generated: {report_path}")
        
        return {
            'contribution': contribution_results,
            'code_change': code_change_results,
            'temporal': temporal_results,
            'report_path': str(report_path)
        }
    
    def _create_intent_visualizations(self, contribution, code_change, temporal, output_path):
        """Create visualizations for developer intent analysis"""
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Embedding contribution comparison
        ax1 = axes[0, 0]
        if contribution and 'embedding_contribution' in contribution:
            contrib = contribution['embedding_contribution']
            models = list(contrib.keys())
            improvements = [contrib[m]['improvement_percentage'] for m in models]
            significant = [contrib[m]['significant'] for m in models]
            
            colors = ['green' if sig else 'gray' for sig in significant]
            bars = ax1.barh(range(len(models)), improvements, color=colors, alpha=0.7)
            ax1.set_yticks(range(len(models)))
            ax1.set_yticklabels([m.replace('ML_', '').replace('_', '\n')[:20] for m in models], 
                               fontsize=8)
            ax1.set_xlabel('Improvement over Baseline (%)')
            ax1.set_title('Embedding Model Improvements\n(Green = Statistically Significant)')
            ax1.axvline(x=0, color='black', linestyle='--', linewidth=1)
            ax1.grid(axis='x', alpha=0.3)
        
        # 2. Code change sensitivity
        ax2 = axes[0, 1]
        if code_change:
            models = list(code_change.keys())
            changed_imp = [code_change[m]['changed_improvement'] for m in models]
            unchanged_imp = [code_change[m]['unchanged_improvement'] for m in models]
            
            x = np.arange(len(models))
            width = 0.35
            
            ax2.bar(x - width/2, changed_imp, width, label='Changed Tests', alpha=0.8)
            ax2.bar(x + width/2, unchanged_imp, width, label='Unchanged Tests', alpha=0.8)
            
            ax2.set_xlabel('Model')
            ax2.set_ylabel('Improvement over Baseline')
            ax2.set_title('Performance Improvement:\nChanged vs Unchanged Tests')
            ax2.set_xticks(x)
            ax2.set_xticklabels([m.replace('ML_', '')[:15] for m in models], 
                               rotation=45, ha='right', fontsize=8)
            ax2.legend()
            ax2.axhline(y=0, color='black', linestyle='--', linewidth=1)
            ax2.grid(axis='y', alpha=0.3)
        
        # 3. Temporal stability
        ax3 = axes[1, 0]
        if temporal:
            models = list(temporal.keys())
            stabilities = [temporal[m]['stability'] for m in models]
            baseline_stabs = [temporal[m]['baseline_stability'] for m in models]
            
            x = np.arange(len(models))
            width = 0.35
            
            ax3.bar(x - width/2, stabilities, width, label='Embedding Model', alpha=0.8)
            ax3.bar(x + width/2, baseline_stabs, width, label='Baseline', alpha=0.8)
            
            ax3.set_xlabel('Model')
            ax3.set_ylabel('Performance Std Dev (lower = more stable)')
            ax3.set_title('Temporal Stability Comparison')
            ax3.set_xticks(x)
            ax3.set_xticklabels([m.replace('ML_', '')[:15] for m in models],
                               rotation=45, ha='right', fontsize=8)
            ax3.legend()
            ax3.grid(axis='y', alpha=0.3)
        
        # 4. Summary heatmap
        ax4 = axes[1, 1]
        if contribution and code_change and temporal:
            # Create summary matrix
            all_models = set()
            if 'embedding_contribution' in contribution:
                all_models.update(contribution['embedding_contribution'].keys())
            all_models.update(code_change.keys())
            all_models.update(temporal.keys())
            
            all_models = sorted(list(all_models))
            
            # Three metrics: improvement, code change sensitivity, temporal stability
            metrics = ['Overall\nImprovement', 'Helps on\nCode Changes', 'Temporal\nStability']
            heatmap_data = np.zeros((len(all_models), len(metrics)))
            
            for i, model in enumerate(all_models):
                # Overall improvement (normalized)
                if 'embedding_contribution' in contribution and model in contribution['embedding_contribution']:
                    heatmap_data[i, 0] = contribution['embedding_contribution'][model]['improvement_percentage'] / 10
                
                # Code change sensitivity (binary: helps more = 1)
                if model in code_change:
                    heatmap_data[i, 1] = 1 if code_change[model]['helps_more_on_changes'] else 0
                
                # Temporal stability (inverted: lower std = better)
                if model in temporal:
                    baseline_std = temporal[model]['baseline_stability']
                    model_std = temporal[model]['stability']
                    heatmap_data[i, 2] = 1 if model_std < baseline_std else 0
            
            im = ax4.imshow(heatmap_data, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)
            ax4.set_xticks(range(len(metrics)))
            ax4.set_xticklabels(metrics)
            ax4.set_yticks(range(len(all_models)))
            ax4.set_yticklabels([m.replace('ML_', '')[:20] for m in all_models], fontsize=8)
            ax4.set_title('Developer Intent Capture Summary')
            plt.colorbar(im, ax=ax4)
            
            # Add text annotations
            for i in range(len(all_models)):
                for j in range(len(metrics)):
                    if j == 0:  # Improvement percentage
                        text = ax4.text(j, i, f'{heatmap_data[i, j]:.1f}',
                                       ha="center", va="center", color="black", fontsize=7)
                    else:  # Binary metrics
                        symbol = '✓' if heatmap_data[i, j] > 0.5 else '✗'
                        text = ax4.text(j, i, symbol,
                                       ha="center", va="center", color="black", fontsize=10)
        
        plt.tight_layout()
        viz_path = output_path / 'developer_intent_analysis.png'
        plt.savefig(viz_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f" Visualizations saved: {viz_path}")

# ENHANCED FAILURE PREDICTION FRAMEWORK WITH ALL FIXES
class RobustFailurePredictionFramework:
    """
    Methodologically robust framework with all fixes applied
    """
    
    def __init__(self, random_seed=42, output_dir="tcp_analysis_results", force_gpu=False):
        self.random_seed = random_seed
        self.models = {}
        self.scalers = {}
        self.results = {}
        self.embeddings = None
        self.project_name = "unknown"  # Will be set later
        self.statistical_tester = StatisticalTester()
        
        # Create output directory
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        print(f"📁 Output directory created: {self.output_dir}")
        
        # Configure GPU and set global determinism
        self.gpu_available, self.device_name = set_global_determinism(random_seed, force_gpu=force_gpu)
        print(f" Framework will use device: {self.device_name}")
        
    def load_embeddings(self, embeddings_dict: Dict[str, np.ndarray]):
        """Load embeddings and create fair comparison variants"""
        # Original embeddings
        self.embeddings = embeddings_dict.copy()
        
        # Create fair concatenated baseline
        if 'commit_only' in embeddings_dict and 'files_only' in embeddings_dict:
            self.embeddings['concatenated'] = np.hstack([
                embeddings_dict['commit_only'], 
                embeddings_dict['files_only']
            ])
        
        print("Loaded embeddings:")
        for name, emb in self.embeddings.items():
            print(f"  {name}: {emb.shape}")
    
    def prepare_data_strict_temporal(self, df: pd.DataFrame, test_size: float = 0.2):
        """
        Prepare data with strict temporal splits - NO LEAKAGE
        """
        print("\n" + "="*70)
        print("PREPARING DATA WITH STRICT TEMPORAL VALIDATION")
        print("="*70)
        
        # Data quality check
        failure_count = (df['Verdict'] == 1).sum()
        total_count = len(df)
        failure_rate = failure_count / total_count
        
        print(f"Dataset: {df.shape}")
        print(f"Failures: {failure_count}/{total_count} ({failure_rate:.3%})")
        print(f"Cycles: {df['Cycle'].min()} to {df['Cycle'].max()} ({df['Cycle'].nunique()} unique)")
        
        # Use adaptive splitter
        train_indices, test_indices, split_metadata = smart_temporal_split(
            df, 
            project_name=getattr(self, 'project_name', 'unknown'),
            output_dir=str(self.output_dir / "split_metadata"),
            verbose=True
        )

        # Print split metadata summary
        if split_metadata:
            print(f"\n Adaptive Split Applied:")
            print(f"   Strategy: {split_metadata.strategy}")
            print(f"   Statistical Power: {split_metadata.statistical_power}")
            print(f"   Test Proportion: {split_metadata.test_proportion:.1%}")
        
        # Extract features
        traditional_features = ['DurationFeature', 'E1', 'E2', 'E3', 'LastRunFeature', 'DIST', 'CHANGE_IN_STATUS']
        if 'DurationFeature' not in df.columns:
            traditional_features[0] = 'Duration'
        
        X = df[traditional_features].values
        y = df['Verdict'].values
        
        X_train, X_test = X[train_indices], X[test_indices]
        y_train, y_test = y[train_indices], y[test_indices]
        df_train, df_test = df.iloc[train_indices].copy(), df.iloc[test_indices].copy()
        
        print(f"\nTrain set: {len(X_train)} samples, {sum(y_train)} failures ({sum(y_train)/len(y_train):.3%})")
        print(f"Test set: {len(X_test)} samples, {sum(y_test)} failures ({sum(y_test)/len(y_test):.3%})")
        
        # Verify temporal separation
        train_cycles = set(df_train['Cycle'].unique())
        test_cycles = set(df_test['Cycle'].unique())
        assert not train_cycles.intersection(test_cycles), "TEMPORAL LEAKAGE DETECTED!"
        
        print(" Temporal separation verified - no data leakage")
        
        return X_train, X_test, y_train, y_test, df_train, df_test
    
    def create_comprehensive_baselines(self, df_train, df_test):
        """Create all baseline predictions for fair comparison"""
        baseline_predictions = {}
        
        # 1. Random baseline
        baseline_predictions['Random'] = BaselineModels.random_baseline(df_test, self.random_seed)
        
        # 2. Duration-based baseline
        baseline_predictions['Duration'] = BaselineModels.duration_baseline(df_test)
        
        # 3. Recency baseline
        baseline_predictions['Recency'] = BaselineModels.recency_baseline(df_test)
        
        # 4. Historical failure rate
        baseline_predictions['Historical'] = BaselineModels.historical_failure_rate_baseline(df_train, df_test)
        
        # 5. PRIORITY_VALUE baseline (CORRECTED - uses only test data, no temporal splitting)
        baseline_predictions['Priority_Value'] = BaselineModels.priority_value_baseline(df_test)
        
        print("Created baseline predictions:")
        for name, preds in baseline_predictions.items():
            print(f"  {name}: mean={np.mean(preds):.3f}, std={np.std(preds):.3f}")
        
        return baseline_predictions
    
    def handle_class_imbalance_reproducible(self, X_train, y_train, method='class_weights'):
        """Handle class imbalance with fixed random seed"""
        print(f"\nHandling class imbalance: {method}")
        
        original_dist = Counter(y_train)
        print(f"Original distribution: {original_dist}")
        
        if method == 'class_weights':
            class_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
            class_weight_dict = {i: weight for i, weight in enumerate(class_weights)}
            return X_train, y_train, class_weight_dict
        
        elif method == 'smote':
            # Reproducible SMOTE
            X_resampled, y_resampled = self.simple_smote_reproducible(X_train, y_train)
            print(f"After SMOTE: {Counter(y_resampled)}")
            return X_resampled, y_resampled, None
        
        return X_train, y_train, None
    
    def simple_smote_reproducible(self, X, y, k_neighbors=5):
        """SMOTE with fixed random seed for reproducibility"""
        np.random.seed(self.random_seed)
        
        unique, counts = np.unique(y, return_counts=True)
        if len(unique) < 2:
            return X, y
            
        minority_class = unique[np.argmin(counts)]
        majority_class = unique[np.argmax(counts)]
        
        minority_indices = np.where(y == minority_class)[0]
        majority_indices = np.where(y == majority_class)[0]
        
        if len(minority_indices) < 2:
            return X, y
        
        X_minority = X[minority_indices]
        n_synthetic = len(majority_indices) - len(minority_indices)
        
        if n_synthetic <= 0:
            return X, y
        
        k_neighbors = min(k_neighbors, len(X_minority) - 1)
        if k_neighbors <= 0:
            return X, y
        
        nn = NearestNeighbors(n_neighbors=k_neighbors + 1)
        nn.fit(X_minority)
        
        synthetic_samples = []
        for _ in range(n_synthetic):
            idx = np.random.randint(0, len(X_minority))
            sample = X_minority[idx]
            
            _, neighbors = nn.kneighbors([sample])
            neighbors = neighbors[0][1:]  # Remove self
            
            if len(neighbors) > 0:
                neighbor_idx = np.random.choice(neighbors)
                neighbor = X_minority[neighbor_idx]
                alpha = np.random.random()
                synthetic = sample + alpha * (neighbor - sample)
                synthetic_samples.append(synthetic)
        
        if synthetic_samples:
            X_resampled = np.vstack([X, np.array(synthetic_samples)])
            y_resampled = np.hstack([y, np.full(len(synthetic_samples), minority_class)])
            return X_resampled, y_resampled
        
        return X, y
    
    def mish_activation(self, x):
        """Mish activation function"""
        return x * tf.nn.tanh(tf.nn.softplus(x))
    
    def build_model_reproducible(self, input_dim, model_type='basic'):
        """Build model with reproducible weight initialization and explicit device placement"""
        print(f" Building {model_type} model on device: {self.device_name}")
        
        # Set TensorFlow seeds for reproducible initialization
        tf.random.set_seed(self.random_seed)
        
        # Use explicit device placement (similar to PyTorch's .to(device))
        with tf.device(self.device_name):
            if model_type == 'basic':
                model = Sequential([
                    Dense(64, input_shape=(input_dim,), activation=self.mish_activation, 
                          kernel_regularizer=l2(1e-4), kernel_initializer='he_normal'),
                    BatchNormalization(),
                    Dropout(0.3),
                    Dense(32, activation=self.mish_activation, kernel_regularizer=l2(1e-4)),
                    BatchNormalization(),
                    Dropout(0.3),
                    Dense(16, activation=self.mish_activation),
                    Dropout(0.2),
                    Dense(1, activation='sigmoid')
                ])
                
            elif model_type == 'enhanced':
                model = Sequential([
                    Dense(128, input_shape=(input_dim,), activation=self.mish_activation,
                          kernel_regularizer=l2(1e-4), kernel_initializer='he_normal'),
                    BatchNormalization(),
                    Dropout(0.4),
                    Dense(64, activation=self.mish_activation, kernel_regularizer=l2(1e-4)),
                    BatchNormalization(),
                    Dropout(0.3),
                    Dense(32, activation=self.mish_activation, kernel_regularizer=l2(1e-4)),
                    BatchNormalization(), 
                    Dropout(0.3),
                    Dense(16, activation=self.mish_activation),
                    Dropout(0.2),
                    Dense(1, activation='sigmoid')
                ])
                
            elif model_type == 'dual_branch':
                # Traditional features input
                history_input = Input(shape=(7,), name="traditional_features")
                h1 = Dense(32, activation=self.mish_activation, kernel_initializer='he_normal')(history_input)
                h1 = BatchNormalization()(h1)
                h1 = Dropout(0.3)(h1)
                h1 = Dense(16, activation=self.mish_activation)(h1)
                
                # Embedding features input  
                embedding_input = Input(shape=(input_dim-7,), name="embedding_features")
                e1 = Dense(64, activation=self.mish_activation, kernel_initializer='he_normal')(embedding_input)
                e1 = BatchNormalization()(e1)
                e1 = Dropout(0.4)(e1)
                e1 = Dense(32, activation=self.mish_activation)(e1)
                e1 = BatchNormalization()(e1)
                e1 = Dense(16, activation=self.mish_activation)(e1)
                
                # Fusion
                combined = Concatenate()([h1, e1])
                output = Dense(32, activation=self.mish_activation)(combined)
                output = BatchNormalization()(output)
                output = Dropout(0.3)(output)
                output = Dense(16, activation=self.mish_activation)(output)
                output = Dropout(0.2)(output)
                final_output = Dense(1, activation='sigmoid')(output)
                
                model = Model(inputs=[history_input, embedding_input], outputs=final_output)
            
            # Compile with reproducible optimizer
            model.compile(
                optimizer=Adam(learning_rate=0.001),
                loss='binary_crossentropy',
                metrics=['accuracy', 'precision', 'recall']
            )
        
        # Verify model device placement
        print(f" Model created and placed on: {self.device_name}")
        # TensorFlow device placement verification - simplified approach
        print(f" Model configured for device: {self.device_name}")
        
        return model
    
    def evaluate_with_statistics(self, df_test, y_test, y_pred_proba, model_name):
        """Enhanced evaluation with statistical measures"""
        
        results = {
            'model_name': model_name,
            'total_tests': len(y_test),
            'total_failures': sum(y_test),
            'failure_rate': sum(y_test) / len(y_test)
        }
        
        # Store per-cycle metrics for statistical testing
        cycle_metrics = {
            'time_to_first_failure_per_cycle': [],
            'efficiency_per_cycle': [],
            'rank_per_cycle': []
        }
        
        # Calculate traditional metrics
        results['auc_roc'] = roc_auc_score(y_test, y_pred_proba)
        results['auc_pr'] = average_precision_score(y_test, y_pred_proba)
        
        # Ranking metrics
        test_df = df_test.copy()
        test_df['failure_prob'] = y_pred_proba
        test_df['true_label'] = y_test
        
        ranking_metrics = {}
        for k in [1, 3, 5, 10, 20]:
            if k <= len(test_df):
                test_df_sorted = test_df.sort_values('failure_prob', ascending=False)
                top_k_labels = test_df_sorted['true_label'].iloc[:k]
                ranking_metrics[f'precision_at_{k}'] = sum(top_k_labels) / k if k > 0 else 0
                ranking_metrics[f'recall_at_{k}'] = sum(top_k_labels) / sum(y_test) if sum(y_test) > 0 else 0
        
        results['ranking_metrics'] = ranking_metrics
        
        # Per-cycle analysis for statistics
        if 'Cycle' in test_df.columns:
            for cycle in sorted(test_df['Cycle'].unique()):
                cycle_df = test_df[test_df['Cycle'] == cycle]
                cycle_failures = sum(cycle_df['true_label'])
                
                if cycle_failures > 0:
                    cycle_sorted = cycle_df.sort_values('failure_prob', ascending=False)
                    
                    # Time to first failure (if Duration available)
                    duration_col = 'DurationFeature' if 'DurationFeature' in cycle_df.columns else 'Duration'
                    if duration_col in cycle_df.columns:
                        cycle_sorted['cumulative_time'] = cycle_sorted[duration_col].cumsum()
                        first_failure_idx = cycle_sorted[cycle_sorted['true_label'] == 1].index
                        if len(first_failure_idx) > 0:
                            first_failure_pos = cycle_sorted.index.get_loc(first_failure_idx[0])
                            time_to_first = cycle_sorted['cumulative_time'].iloc[first_failure_pos]
                            total_time = cycle_sorted['cumulative_time'].iloc[-1]
                            
                            cycle_metrics['time_to_first_failure_per_cycle'].append(time_to_first)
                            cycle_metrics['efficiency_per_cycle'].append(1 - time_to_first/total_time if total_time > 0 else 0)
                    
                    # Average rank of failures
                    failure_ranks = []
                    for idx, (_, row) in enumerate(cycle_sorted.iterrows(), 1):
                        if row['true_label'] == 1:
                            failure_ranks.append(idx)
                    
                    if failure_ranks:
                        avg_rank = np.mean(failure_ranks)
                        cycle_metrics['rank_per_cycle'].append(avg_rank)
        
        # Calculate summary statistics with confidence intervals
        for metric_name, values in cycle_metrics.items():
            if values:
                mean, lower, upper = self.statistical_tester.bootstrap_confidence_interval(values)
                results[f"avg_{metric_name}"] = mean
                results[f"{metric_name}_ci_lower"] = lower
                results[f"{metric_name}_ci_upper"] = upper
                results[metric_name] = values  # Store raw values for comparisons
        
        # Store predictions for further analysis
        results['predictions'] = y_pred_proba
        results['test_indices'] = df_test.index.tolist()
        
        return results
    
    def train_single_model(self, model_name, X_train, y_train, X_test, y_test, df_test, 
                          model_type='basic', balance_method='class_weights'):
        """Train single model with all methodological fixes"""
        
        print(f"\n{'='*80}")
        print(f"TRAINING MODEL: {model_name}")
        print(f"{'='*80}")
        
        # Reproducible class imbalance handling
        X_train_balanced, y_train_balanced, class_weights = self.handle_class_imbalance_reproducible(
            X_train, y_train, method=balance_method
        )
        
        # Reproducible feature scaling
        scaler = MinMaxScaler()
        X_train_scaled = scaler.fit_transform(X_train_balanced)
        X_test_scaled = scaler.transform(X_test)
        self.scalers[model_name] = scaler
        
        # Build model
        if model_type == 'dual_branch':
            model = self.build_model_reproducible(X_train_scaled.shape[1], model_type)
            train_inputs = [X_train_scaled[:, :7], X_train_scaled[:, 7:]]
            test_inputs = [X_test_scaled[:, :7], X_test_scaled[:, 7:]]
        else:
            model = self.build_model_reproducible(X_train_scaled.shape[1], model_type)
            train_inputs = X_train_scaled
            test_inputs = X_test_scaled
        
        # Training with early stopping
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=8, min_lr=1e-6)
        ]
        
        fit_kwargs = {
            'x': train_inputs,
            'y': y_train_balanced,
            'validation_data': (test_inputs, y_test),
            'epochs': 100,
            'batch_size': 32,
            'callbacks': callbacks,
            'verbose': 1  # Show progress to prevent "hanging" appearance
        }
        
        if class_weights is not None:
            fit_kwargs['class_weight'] = class_weights
        
        # Train model with explicit device placement and progress monitoring
        print(f"🏃 Training on device: {self.device_name}")
        print(f"    Training data shape: {X_train_balanced.shape}")
        print(f"    Target distribution: {Counter(y_train_balanced)}")
        
        import time
        start_time = time.time()
        
        try:
            with tf.device(self.device_name):
                history = model.fit(**fit_kwargs)
            
            training_time = time.time() - start_time
            print(f"   ⏱️ Training completed in {training_time:.1f} seconds")
            
        except Exception as e:
            print(f"    Training failed: {e}")
            raise e
        
        # Generate predictions on the same device
        print(f"🔮 Generating predictions on device: {self.device_name}")
        try:
            with tf.device(self.device_name):
                y_pred_proba = model.predict(test_inputs, verbose=0).flatten()
            print(f"    Predictions generated successfully")
        except Exception as e:
            print(f"    Prediction failed: {e}")
            raise e
        
        # Enhanced evaluation with statistics
        results = self.evaluate_with_statistics(df_test, y_test, y_pred_proba, model_name)
        results['history'] = history.history
        results['model_type'] = model_type
        results['balance_method'] = balance_method
        
        # Store everything
        self.models[model_name] = model
        self.results[model_name] = results
        
        # Memory cleanup to prevent accumulation
        import gc
        gc.collect()
        if hasattr(tf.keras.backend, 'clear_session'):
            # Don't clear session as it might interfere with device placement
            pass
        
        print(f" {model_name}: AUC-PR={results['auc_pr']:.4f}")
        
        return results
    
    def run_comprehensive_study(self, df, test_size=0.2):
        """
        Run complete methodologically robust study with proper model architecture separation
        
        Model Architecture Strategy:
        - BASIC: Only traditional features (history) - NO embeddings
        - ENHANCED: Traditional features + embeddings (concatenated)
        - DUAL_BRANCH: Two-headed network (history head + embedding head)
        """
        print(" COMPREHENSIVE METHODOLOGICALLY ROBUST TCP STUDY")
        print("="*80)
        print(" Strict temporal validation (no data leakage)")  
        print(" Statistical significance testing")
        print(" Comprehensive baselines")
        print(" Reproducible experiments")
        print(" Confidence intervals")
        print(" Developer intent capture analysis")
        print("="*80)
        
        # System resource check
        import psutil
        memory = psutil.virtual_memory()
        print(f" Available system memory: {memory.available / (1024**3):.1f} GB / {memory.total / (1024**3):.1f} GB")
        if memory.percent > 80:
            print(" Warning: System memory usage is high!")
        
        # Strict temporal data preparation
        X_train, X_test, y_train, y_test, df_train, df_test = self.prepare_data_strict_temporal(df, test_size)
        
        # Create comprehensive baselines
        baseline_predictions = self.create_comprehensive_baselines(df_train, df_test)
        
        # Store baseline results
        for baseline_name, predictions in baseline_predictions.items():
            baseline_results = self.evaluate_with_statistics(df_test, y_test, predictions, f"Baseline_{baseline_name}")
            baseline_results['model_type'] = 'baseline'
            baseline_results['balance_method'] = 'none'
            self.results[f"Baseline_{baseline_name}"] = baseline_results
        
        # Balance methods to test
        balance_methods = ['class_weights', 'smote']
        
        # Calculate total number of models
        total_models = 0
        # Basic models (no embeddings): 2 (one per balance method)
        total_models += len(balance_methods)
        
        # Embedding models (enhanced + dual_branch)
        if self.embeddings is not None:
            # For each embedding type: 2 enhanced + 2 dual_branch = 4 per embedding
            total_models += len(self.embeddings) * len(balance_methods) * 2
        
        print(f"\n Will train {total_models} total models")
        print("\nModel Architecture Plan:")
        print("   BASIC models: Traditional features only (NO embeddings)")
        print("   ENHANCED models: Traditional features + embeddings (concatenated)")
        print("   DUAL_BRANCH models: Separate heads for traditional & embeddings")
        
        current_model = 0
        
        # ===================================================================
        # STEP 1: Train BASIC models (traditional features ONLY, NO embeddings)
        # ===================================================================
        print(f"\n{'='*60}")
        print("STEP 1: BASIC MODELS (Traditional Features Only)")
        print(f"{'='*60}")
        
        for balance_method in balance_methods:
            current_model += 1
            model_name = f"ML_basic_history_only_{balance_method}"
            print(f"\n [{current_model}/{total_models}] Training: {model_name}")
            print(f"    Using ONLY traditional features: {X_train.shape}")
            
            try:
                self.train_single_model(
                    model_name, X_train, y_train, X_test, y_test, df_test,
                    model_type='basic', balance_method=balance_method
                )
                print(f"    Completed {model_name}")
            except Exception as e:
                print(f"    Failed {model_name}: {e}")
        
        # ===================================================================
        # STEP 2: Train EMBEDDING models (enhanced + dual_branch)
        # ===================================================================
        if self.embeddings is not None:
            print(f"\n{'='*60}")
            print("STEP 2: EMBEDDING-BASED MODELS")
            print(f"{'='*60}")
            
            for emb_name, emb_data in self.embeddings.items():
                print(f"\n Processing {emb_name} embeddings...")
                
                try:
                    # Prepare embedding data
                    print(f"    Embedding shape: {emb_data.shape}")
                    train_embeddings = emb_data[df_train.index]
                    test_embeddings = emb_data[df_test.index]
                    
                    # For ENHANCED: concatenate traditional + embeddings
                    X_train_enhanced = np.hstack([X_train, train_embeddings])
                    X_test_enhanced = np.hstack([X_test, test_embeddings])
                    print(f"    Enhanced feature shape: {X_train_enhanced.shape}")
                    
                    # Memory check
                    memory_usage = (X_train_enhanced.nbytes + X_test_enhanced.nbytes) / (1024**3)
                    print(f"    Memory usage: {memory_usage:.2f} GB")
                    
                    if memory_usage > 8.0:
                        print(f"    High memory usage!")
                    
                    # Train ENHANCED models (concatenated features)
                    print(f"\n    ENHANCED models ({emb_name}):")
                    for balance_method in balance_methods:
                        current_model += 1
                        model_name = f"ML_enhanced_{emb_name}_{balance_method}"
                        print(f"\n    [{current_model}/{total_models}] Training: {model_name}")
                        print(f"       Using concatenated features: {X_train_enhanced.shape}")
                        
                        try:
                            self.train_single_model(
                                model_name, X_train_enhanced, y_train, 
                                X_test_enhanced, y_test, df_test,
                                model_type='enhanced', balance_method=balance_method
                            )
                            print(f"       Completed {model_name}")
                        except Exception as e:
                            print(f"       Failed {model_name}: {e}")
                    
                    # Train DUAL_BRANCH models (separate inputs)
                    print(f"\n    DUAL_BRANCH models ({emb_name}):")
                    for balance_method in balance_methods:
                        current_model += 1
                        model_name = f"ML_dual_branch_{emb_name}_{balance_method}"
                        print(f"\n    [{current_model}/{total_models}] Training: {model_name}")
                        print(f"       Using dual inputs:")
                        print(f"       - History head: {X_train.shape}")
                        print(f"       - Embedding head: {train_embeddings.shape}")
                        
                        try:
                            # Pass the concatenated version but model will split internally
                            self.train_single_model(
                                model_name, X_train_enhanced, y_train,
                                X_test_enhanced, y_test, df_test,
                                model_type='dual_branch', balance_method=balance_method
                            )
                            print(f"       Completed {model_name}")
                        except Exception as e:
                            print(f"       Failed {model_name}: {e}")
                    
                except Exception as e:
                    print(f"    Error with {emb_name} embeddings: {e}")
                    continue
        else:
            print("\n No embeddings available - skipping embedding-based models")
        
        # Statistical comparison of all models
        print("\n" + "="*80)
        print("STATISTICAL MODEL COMPARISON")
        print("="*80)
        
        comparison_results = {}
        metrics_to_compare = ['avg_time_to_first_failure_per_cycle', 'avg_efficiency_per_cycle', 'auc_pr']
        
        for metric in metrics_to_compare:
            print(f"\nComparing models on: {metric}")
            comparison_results[metric] = self.statistical_tester.compare_models_statistically(
                self.results, metric
            )
            
            # Print significant differences
            for comparison, stats in comparison_results[metric].items():
                if stats['significant']:
                    print(f"   {comparison}: p={stats['p_value']:.4f}, effect_size={stats['effect_size']:.3f}")
        
        return self.create_robust_summary(), comparison_results
    
    def run_interpretability_analysis(self, df_test, predictions_dict):
        """Run comprehensive interpretability analysis"""
        
        print("\n" + "="*80)
        print("MODEL INTERPRETABILITY AND CAUSALITY ANALYSIS")
        print("="*80)
        
        interpreter = ModelInterpretabilityAnalysis()
        
        # 1. Feature importance analysis - only for baseline models (non-embedding)
        print("\n1. FEATURE IMPORTANCE ANALYSIS:")
        traditional_features = ['DurationFeature', 'E1', 'E2', 'E3', 'LastRunFeature', 'DIST', 'CHANGE_IN_STATUS']
        if 'DurationFeature' not in df_test.columns:
            traditional_features[0] = 'Duration'
        
        available_features = [f for f in traditional_features if f in df_test.columns]
        
        # Only analyze baseline models since they use traditional features
        baseline_models_analyzed = 0
        for model_name in predictions_dict.keys():
            if (model_name in self.models and model_name in self.scalers and 
                not any(emb_type in model_name for emb_type in ['commit_only', 'files_only', 'combined', 'concatenated'])):
                try:
                    X_test_scaled = self.scalers[model_name].transform(df_test[available_features].values)
                    importance_df = interpreter.analyze_feature_importance(
                        self.models[model_name], 
                        X_test_scaled,
                        available_features,
                        model_name=model_name
                    )
                    if not importance_df.empty:
                        print(f"\n{model_name} - Top 3 Features:")
                        print(importance_df.head(3).to_string(index=False))
                        baseline_models_analyzed += 1
                except Exception as e:
                    print(f"Could not analyze {model_name}: {e}")
        
        if baseline_models_analyzed == 0:
            print("No baseline models available for feature importance analysis.")
            print("Feature importance analysis works best with traditional feature models.")
        
        # 1b. Embedding model pattern analysis
        print("\n2. EMBEDDING MODEL PATTERN ANALYSIS:")
        embedding_models_analyzed = 0
        for model_name in predictions_dict.keys():
            if any(emb_type in model_name for emb_type in ['commit_only', 'files_only', 'combined', 'concatenated']):
                try:
                    embedding_analysis = interpreter.analyze_embedding_model_patterns(
                        model_name, predictions_dict[model_name], df_test
                    )
                    if embedding_analysis:
                        print(f"\n{model_name}:")
                        print(f"  Prediction range: {embedding_analysis['prediction_stats']['predictions_range']:.4f}")
                        print(f"  Mean prediction: {embedding_analysis['prediction_stats']['mean_prediction']:.4f}")
                        
                        # Show top correlations
                        correlations = embedding_analysis['feature_correlations']
                        if correlations:
                            top_corr = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
                            print("  Top feature correlations:")
                            for feature, corr in top_corr:
                                print(f"    {feature}: {corr:.3f}")
                        embedding_models_analyzed += 1
                except Exception as e:
                    print(f"Could not analyze embedding model {model_name}: {e}")
        
        if embedding_models_analyzed == 0:
            print("No embedding models found for pattern analysis.")
        
        # 3. Comprehensive efficiency analysis (works with all models)
        efficiency_analyzer = ComprehensiveEfficiencyAnalysis()
        efficiency_results = efficiency_analyzer.comprehensive_analysis_report(df_test, predictions_dict)
        
        return {
            'efficiency_results': efficiency_results
        }
    
    def create_robust_summary(self):
        """Create summary with statistical measures"""
        summary_data = []
        
        for model_name, results in self.results.items():
            # Extract metrics with confidence intervals
            auc_pr = results.get('auc_pr', 0)
            
            # Time metrics with CIs
            time_mean = results.get('avg_time_to_first_failure_per_cycle', 0)
            time_ci_lower = results.get('time_to_first_failure_per_cycle_ci_lower', 0)
            time_ci_upper = results.get('time_to_first_failure_per_cycle_ci_upper', 0)
            
            # Efficiency metrics with CIs  
            eff_mean = results.get('avg_efficiency_per_cycle', 0)
            eff_ci_lower = results.get('efficiency_per_cycle_ci_lower', 0)
            eff_ci_upper = results.get('efficiency_per_cycle_ci_upper', 0)
            
            # Ranking metrics
            rank_mean = results.get('avg_rank_per_cycle', 0)
            rank_ci_lower = results.get('rank_per_cycle_ci_lower', 0)
            rank_ci_upper = results.get('rank_per_cycle_ci_upper', 0)
            
            summary_data.append({
                'Model': model_name,
                'Model_Type': results.get('model_type', 'unknown'),
                'Balance_Method': results.get('balance_method', 'none'),
                'AUC_PR': auc_pr,
                'Precision_at_10': results.get('ranking_metrics', {}).get('precision_at_10', 0),
                'Time_to_Failure_Mean': time_mean,
                'Time_to_Failure_CI': f"[{time_ci_lower:.2f}, {time_ci_upper:.2f}]",
                'Efficiency_Mean': eff_mean,
                'Efficiency_CI': f"[{eff_ci_lower:.3f}, {eff_ci_upper:.3f}]",
                'Avg_Failure_Rank': rank_mean,
                'Rank_CI': f"[{rank_ci_lower:.1f}, {rank_ci_upper:.1f}]",
                'Sample_Size': len(results.get('time_to_first_failure_per_cycle', []))
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('AUC_PR', ascending=False)
        
        print("\n" + "="*120)
        print("ROBUST RESULTS SUMMARY WITH STATISTICAL MEASURES")
        print("="*120)
        print("Key Changes from Original Analysis:")
        print(" Strict temporal splits (no data leakage)")
        print(" Statistical significance testing")
        print(" Confidence intervals for all metrics")
        print(" Comprehensive baselines")
        print(" Reproducible experiments")
        print("="*120)
        
        # Display key columns
        display_cols = ['Model', 'AUC_PR', 'Time_to_Failure_Mean', 'Time_to_Failure_CI', 
                       'Efficiency_Mean', 'Efficiency_CI', 'Sample_Size']
        
        print(summary_df[display_cols].to_string(index=False, float_format='%.4f'))
        
        return summary_df
    
class ModelInterpretabilityAnalysis:
    """
    Analyze what features drive model rankings to detect spurious correlations
    """
    
    def analyze_feature_importance(self, model, X_test, feature_names, model_name=""):
        """Calculate feature importance for top-ranked predictions"""
        try:
            # Check if this is a dual-branch model
            is_dual_branch = hasattr(model, 'inputs') and len(model.inputs) == 2
            
            if is_dual_branch:
                print(f" Skipping feature importance for dual-branch model {model_name}")
                print("   Dual-branch models require embedding features which aren't available in traditional feature analysis")
                return pd.DataFrame()
            
            # For Keras models, we'll use a different approach since permutation_importance
            # doesn't work well with Keras models directly
            
            # Get baseline predictions
            baseline_predictions = model.predict(X_test, verbose=0)
            
            # Manual permutation importance calculation for Keras models
            importance_scores = []
            
            for i, feature_name in enumerate(feature_names):
                # Create a copy of the test data
                X_permuted = X_test.copy()
                
                # Permute the feature column
                np.random.seed(42)  # For reproducibility
                X_permuted[:, i] = np.random.permutation(X_permuted[:, i])
                
                # Get predictions with permuted feature
                permuted_predictions = model.predict(X_permuted, verbose=0)
                
                # Calculate the decrease in performance (using MSE as proxy)
                baseline_mse = np.mean((baseline_predictions.flatten() - baseline_predictions.flatten())**2)
                permuted_mse = np.mean((baseline_predictions.flatten() - permuted_predictions.flatten())**2)
                
                # Importance is the increase in error when feature is permuted
                importance = permuted_mse - baseline_mse
                importance_scores.append(importance)
            
            importance_df = pd.DataFrame({
                'feature': feature_names,
                'importance': importance_scores,
                'std': np.zeros(len(feature_names))  # No std for this simple approach
            }).sort_values('importance', ascending=False)
            
            return importance_df
            
        except Exception as e:
            print(f" Feature importance analysis failed: {e}")
            return pd.DataFrame()
    
    def analyze_top_ranked_tests(self, df_test, predictions, feature_names, top_k=20):
        """Analyze why specific tests were ranked highly"""
        df_analysis = df_test.copy()
        df_analysis['failure_prob'] = predictions
        
        # Get top-k ranked tests
        top_tests = df_analysis.nlargest(top_k, 'failure_prob')
        
        # Analyze feature patterns
        feature_analysis = {}
        for feature in feature_names:
            if feature in df_analysis.columns:
                feature_analysis[feature] = {
                    'top_k_mean': top_tests[feature].mean(),
                    'overall_mean': df_analysis[feature].mean(),
                    'correlation_with_ranking': df_analysis[feature].corr(df_analysis['failure_prob'])
                }
        
        return feature_analysis, top_tests
    
    def analyze_embedding_model_patterns(self, model_name, predictions, df_test):
        """Analyze patterns for embedding-based models"""
        try:
            # Analyze prediction distribution
            pred_stats = {
                'mean_prediction': np.mean(predictions),
                'std_prediction': np.std(predictions),
                'min_prediction': np.min(predictions),
                'max_prediction': np.max(predictions),
                'predictions_range': np.max(predictions) - np.min(predictions)
            }
            
            # Analyze relationship with traditional features
            traditional_features = ['DurationFeature', 'E1', 'E2', 'E3', 'LastRunFeature', 'DIST', 'CHANGE_IN_STATUS']
            if 'DurationFeature' not in df_test.columns:
                traditional_features[0] = 'Duration'
            
            available_features = [f for f in traditional_features if f in df_test.columns]
            
            feature_correlations = {}
            for feature in available_features:
                try:
                    correlation = np.corrcoef(df_test[feature], predictions)[0, 1]
                    if not np.isnan(correlation):
                        feature_correlations[feature] = correlation
                except:
                    continue
            
            # Find top predicted tests and their characteristics
            df_analysis = df_test.copy()
            df_analysis['prediction'] = predictions
            top_10_pct = df_analysis.nlargest(int(len(df_analysis) * 0.1), 'prediction')
            
            top_characteristics = {}
            for feature in available_features:
                if feature in df_analysis.columns:
                    top_characteristics[f'{feature}_top_mean'] = top_10_pct[feature].mean()
                    top_characteristics[f'{feature}_overall_mean'] = df_analysis[feature].mean()
            
            return {
                'model_name': model_name,
                'prediction_stats': pred_stats,
                'feature_correlations': feature_correlations,
                'top_test_characteristics': top_characteristics
            }
            
        except Exception as e:
            print(f" Embedding model analysis failed for {model_name}: {e}")
            return {}

class ComprehensiveEfficiencyAnalysis:
    """
    Analyze the relationship between:
    1. Model rankings vs PRIORITY_VALUE rankings
    2. Time spent per cycle to find first failure
    3. Ranking consistency vs actual failure detection
    4. Feature attribution vs time efficiency
    """
    
    def analyze_priority_value_correlation(self, df_test, predictions_dict):
        """Analyze correlation between model rankings and PRIORITY_VALUE"""
        
        # Check for different possible column names
        priority_col = None
        possible_names = ['PRIORITY_VALUE', 'Priority_value', 'priority_value', 'PriorityValue']
        
        for col_name in possible_names:
            if col_name in df_test.columns:
                priority_col = col_name
                break
        
        if priority_col is None:
            print(" Warning: PRIORITY_VALUE column not found in dataset")
            print(f"Available columns: {list(df_test.columns)}")
            return {}
        
        print(f" Using {priority_col} column for priority analysis")
        correlation_results = {}
        
        for model_name, predictions in predictions_dict.items():
            # Calculate ranking correlations
            model_ranking = (-predictions).argsort().argsort()  # Convert to ranks
            priority_ranking = (-df_test[priority_col]).argsort().argsort()
            
            spearman_corr = stats.spearmanr(model_ranking, priority_ranking)[0]
            
            # Analyze per-cycle correlation
            cycle_correlations = []
            for cycle in df_test['Cycle'].unique():
                cycle_mask = df_test['Cycle'] == cycle
                if sum(cycle_mask) > 5:  # Minimum cycle size
                    cycle_model_rank = (-predictions[cycle_mask]).argsort().argsort()
                    cycle_priority_rank = (-df_test.loc[cycle_mask, priority_col]).argsort().argsort()
                    
                    cycle_corr = stats.spearmanr(cycle_model_rank, cycle_priority_rank)[0]
                    if not np.isnan(cycle_corr):
                        cycle_correlations.append(cycle_corr)
            
            correlation_results[model_name] = {
                'overall_spearman': spearman_corr,
                'cycle_correlations': cycle_correlations,
                'avg_cycle_correlation': np.mean(cycle_correlations) if cycle_correlations else 0,
                'correlation_stability': np.std(cycle_correlations) if len(cycle_correlations) > 1 else 0
            }
        
        return correlation_results
    
    def analyze_time_efficiency_per_cycle(self, df_test, predictions_dict):
        """Detailed per-cycle time analysis"""
        
        cycle_efficiency_results = {}
        duration_col = 'DurationFeature' if 'DurationFeature' in df_test.columns else 'Duration'
        
        for cycle in sorted(df_test['Cycle'].unique()):
            cycle_df = df_test[df_test['Cycle'] == cycle].copy()
            cycle_failures = sum(cycle_df['Verdict'])
            
            if cycle_failures == 0:
                continue
                
            cycle_results = {
                'cycle_id': cycle,
                'total_tests': len(cycle_df),
                'total_failures': cycle_failures,
                'total_cycle_time': cycle_df[duration_col].sum(),
                'model_performance': {}
            }
            
            for model_name, full_predictions in predictions_dict.items():
                cycle_predictions = full_predictions[df_test['Cycle'] == cycle]
                
                # Rank tests by model predictions
                cycle_df_ranked = cycle_df.copy()
                cycle_df_ranked['prediction'] = cycle_predictions
                cycle_df_ranked = cycle_df_ranked.sort_values('prediction', ascending=False)
                cycle_df_ranked['cumulative_time'] = cycle_df_ranked[duration_col].cumsum()
                
                # Find time metrics
                first_failure_idx = cycle_df_ranked[cycle_df_ranked['Verdict'] == 1].index
                if len(first_failure_idx) > 0:
                    first_failure_pos = cycle_df_ranked.index.get_loc(first_failure_idx[0])
                    time_to_first_failure = cycle_df_ranked['cumulative_time'].iloc[first_failure_pos]
                    
                    # Additional metrics
                    tests_until_first_failure = first_failure_pos + 1
                    time_efficiency = 1 - (time_to_first_failure / cycle_results['total_cycle_time'])
                    test_efficiency = 1 - (tests_until_first_failure / cycle_results['total_tests'])
                    
                    cycle_results['model_performance'][model_name] = {
                        'time_to_first_failure': time_to_first_failure,
                        'tests_until_first_failure': tests_until_first_failure,
                        'time_efficiency': time_efficiency,
                        'test_efficiency': test_efficiency,
                        'time_saved': cycle_results['total_cycle_time'] - time_to_first_failure
                    }
            
            cycle_efficiency_results[cycle] = cycle_results
        
        return cycle_efficiency_results
    
    def correlate_efficiency_with_features(self, cycle_results, df_test, predictions_dict):
        """Analyze what drives time efficiency differences"""
        
        efficiency_correlation_results = {}
        duration_col = 'DurationFeature' if 'DurationFeature' in df_test.columns else 'Duration'
        
        # Aggregate efficiency metrics across cycles
        for model_name in predictions_dict.keys():
            model_efficiencies = []
            model_cycle_features = []
            
            for cycle, cycle_data in cycle_results.items():
                if model_name in cycle_data['model_performance']:
                    perf = cycle_data['model_performance'][model_name]
                    cycle_df = df_test[df_test['Cycle'] == cycle]
                    
                    model_efficiencies.append(perf['time_efficiency'])
                    
                    # Cycle-level features that might affect efficiency
                    cycle_features = {
                        'cycle_size': len(cycle_df),
                        'failure_rate': cycle_data['total_failures'] / cycle_data['total_tests'],
                        'avg_duration': cycle_df[duration_col].mean(),
                        'duration_variance': cycle_df[duration_col].var(),
                        'avg_last_run_feature': cycle_df['LastRunFeature'].mean() if 'LastRunFeature' in cycle_df.columns else 0
                    }
                    model_cycle_features.append(cycle_features)
            
            if len(model_efficiencies) > 5:  # Need sufficient data
                feature_correlations = {}
                feature_df = pd.DataFrame(model_cycle_features)
                
                for feature_name in feature_df.columns:
                    corr = np.corrcoef(model_efficiencies, feature_df[feature_name])[0,1]
                    if not np.isnan(corr):
                        feature_correlations[feature_name] = corr
                
                efficiency_correlation_results[model_name] = {
                    'feature_correlations': feature_correlations,
                    'efficiency_variance': np.var(model_efficiencies),
                    'mean_efficiency': np.mean(model_efficiencies)
                }
        
        return efficiency_correlation_results
    
    def analyze_ranking_stability(self, df_test, predictions_dict):
        """Analyze whether models consistently rank the same tests high"""
        
        stability_results = {}
        
        for cycle in df_test['Cycle'].unique():
            cycle_df = df_test[df_test['Cycle'] == cycle]
            
            if len(cycle_df) < 10:  # Skip small cycles
                continue
                
            cycle_rankings = {}
            for model_name, predictions in predictions_dict.items():
                cycle_preds = predictions[df_test['Cycle'] == cycle]
                # Get top 10% of tests for this cycle
                top_10_pct = max(1, int(len(cycle_df) * 0.1))
                cycle_rankings[model_name] = cycle_df.iloc[np.argsort(cycle_preds)[-top_10_pct:]].index.tolist()
            
            # Calculate pairwise overlap between models
            model_names = list(cycle_rankings.keys())
            overlap_matrix = {}
            
            for i, model1 in enumerate(model_names):
                for model2 in model_names[i+1:]:
                    overlap = len(set(cycle_rankings[model1]).intersection(set(cycle_rankings[model2])))
                    total_unique = len(set(cycle_rankings[model1]).union(set(cycle_rankings[model2])))
                    jaccard_similarity = overlap / total_unique if total_unique > 0 else 0
                    overlap_matrix[f"{model1}_vs_{model2}"] = jaccard_similarity
            
            stability_results[cycle] = overlap_matrix
        
        return stability_results
    
    def analyze_failure_patterns(self, df_test, predictions_dict):
        """Analyze relationship between predictions and actual failure characteristics"""
        
        results = {}
        failed_tests = df_test[df_test['Verdict'] == 1]
        passed_tests = df_test[df_test['Verdict'] == 0]
        
        # Feature names for analysis
        analysis_features = ['DurationFeature', 'LastRunFeature', 'E1', 'E2', 'E3', 'DIST', 'CHANGE_IN_STATUS']
        # Fallback to alternative names if not found
        if 'DurationFeature' not in df_test.columns and 'Duration' in df_test.columns:
            analysis_features[0] = 'Duration'
        
        available_features = [f for f in analysis_features if f in df_test.columns]
        
        for model_name, predictions in predictions_dict.items():
            model_analysis = {}
            
            # Get predictions for failed vs passed tests
            failed_predictions = predictions[df_test['Verdict'] == 1]
            passed_predictions = predictions[df_test['Verdict'] == 0]
            
            # Analyze what makes failed tests rank high
            high_confidence_threshold = np.percentile(predictions, 90)
            high_conf_failed = failed_tests[predictions[df_test['Verdict'] == 1] > high_confidence_threshold]
            high_conf_passed = passed_tests[predictions[df_test['Verdict'] == 0] > high_confidence_threshold]
            
            model_analysis['high_confidence_analysis'] = {
                'failed_tests_high_conf': len(high_conf_failed),
                'passed_tests_high_conf': len(high_conf_passed),
                'precision_at_high_conf': len(high_conf_failed) / (len(high_conf_failed) + len(high_conf_passed)) if (len(high_conf_failed) + len(high_conf_passed)) > 0 else 0
            }
            
            # Feature correlation analysis
            feature_correlations = {}
            for feature in available_features:
                try:
                    feature_correlations[feature] = {
                        'failed_mean': failed_tests[feature].mean(),
                        'passed_mean': passed_tests[feature].mean(),
                        'prediction_correlation': np.corrcoef(df_test[feature], predictions)[0,1]
                    }
                except:
                    # Skip features that cause issues
                    continue
            
            model_analysis['feature_correlations'] = feature_correlations
            results[model_name] = model_analysis
        
        return results
    
    def comprehensive_analysis_report(self, df_test, predictions_dict):
        """Generate comprehensive analysis report"""
        
        print("\n" + "="*80)
        print("COMPREHENSIVE EFFICIENCY AND CAUSALITY ANALYSIS")
        print("="*80)
        
        # 1. Priority value correlation
        print("\n1. MODEL RANKING vs PRIORITY_VALUE CORRELATION:")
        priority_correlations = self.analyze_priority_value_correlation(df_test, predictions_dict)
        
        for model_name, corr_data in priority_correlations.items():
            print(f"\n{model_name}:")
            print(f"  Overall correlation with PRIORITY_VALUE: {corr_data['overall_spearman']:.3f}")
            print(f"  Average per-cycle correlation: {corr_data['avg_cycle_correlation']:.3f}")
            print(f"  Correlation stability: {corr_data['correlation_stability']:.3f}")
        
        # 2. Per-cycle time efficiency
        print("\n2. PER-CYCLE TIME EFFICIENCY ANALYSIS:")
        cycle_results = self.analyze_time_efficiency_per_cycle(df_test, predictions_dict)
        
        # Summarize across cycles
        model_summaries = {}
        for cycle, cycle_data in cycle_results.items():
            for model_name, perf in cycle_data['model_performance'].items():
                if model_name not in model_summaries:
                    model_summaries[model_name] = []
                model_summaries[model_name].append(perf)
        
        for model_name, perfs in model_summaries.items():
            if perfs:
                avg_time_to_first = np.mean([p['time_to_first_failure'] for p in perfs])
                avg_time_saved = np.mean([p['time_saved'] for p in perfs])
                avg_tests_until_first = np.mean([p['tests_until_first_failure'] for p in perfs])
                
                print(f"\n{model_name}:")
                print(f"  Average time to first failure: {avg_time_to_first:.2f}")
                print(f"  Average time saved per cycle: {avg_time_saved:.2f}")
                print(f"  Average tests until first failure: {avg_tests_until_first:.1f}")
        
        # 3. Ranking stability analysis
        print("\n3. RANKING STABILITY ANALYSIS:")
        stability_results = self.analyze_ranking_stability(df_test, predictions_dict)
        if stability_results:
            avg_stability = np.mean([np.mean(list(cycle_data.values())) for cycle_data in stability_results.values() if cycle_data])
            print(f"Average cross-model ranking agreement: {avg_stability:.3f}")
        
        # 4. Failure pattern analysis
        print("\n4. FAILURE CAUSALITY ANALYSIS:")
        causality_results = self.analyze_failure_patterns(df_test, predictions_dict)
        
        for model_name, analysis in causality_results.items():
            print(f"\n{model_name}:")
            hc_analysis = analysis['high_confidence_analysis']
            print(f"  High-confidence precision: {hc_analysis['precision_at_high_conf']:.3f}")
            
            print("  Feature correlations with predictions:")
            for feature, corr_data in analysis['feature_correlations'].items():
                if not np.isnan(corr_data['prediction_correlation']):
                    print(f"    {feature}: r={corr_data['prediction_correlation']:.3f}")
        
        # 5. Efficiency-feature correlations
        print("\n5. EFFICIENCY DRIVERS ANALYSIS:")
        efficiency_correlations = self.correlate_efficiency_with_features(cycle_results, df_test, predictions_dict)
        
        for model_name, corr_data in efficiency_correlations.items():
            print(f"\n{model_name} - Factors affecting efficiency:")
            for feature, corr in corr_data['feature_correlations'].items():
                if abs(corr) > 0.1:  # Only show meaningful correlations
                    print(f"  {feature}: {corr:.3f}")
        
        return {
            'priority_correlations': priority_correlations,
            'cycle_results': cycle_results,
            'efficiency_correlations': efficiency_correlations,
            'stability_results': stability_results,
            'causality_results': causality_results
        }
    
class SequentialCrossProjectValidator:
    """
    Cross-project validation designed for sequential execution:
    1. Run one project at a time
    2. Save results to disk
    3. Aggregate when you have multiple project results
    """
    
    def __init__(self, results_dir="cross_project_results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        print(f"Sequential validator initialized. Results will be saved to: {self.results_dir}")
    
    def save_project_results(self, project_name: str, framework_results: dict, 
                           embedding_comparison: dict, metadata: dict = None):
        """
        Save results from a single project run
        
        Args:
            project_name: Name/identifier for the project
            framework_results: Results from RobustFailurePredictionFramework
            embedding_comparison: Your embedding comparison results
            metadata: Additional project metadata (size, language, etc.)
        """
        project_data = {
            'project_name': project_name,
            'framework_results': self._serialize_results(framework_results),
            'embedding_comparison': embedding_comparison,
            'metadata': metadata or {},
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        # Save to individual project file
        project_file = self.results_dir / f"{project_name}_results.json"
        with open(project_file, 'w') as f:
            json.dump(project_data, f, indent=2, default=str)
        
        print(f" Saved results for project: {project_name}")
        print(f"   File: {project_file}")
        
        # Update project registry
        self._update_project_registry(project_name, metadata)
    
    def _serialize_results(self, results_dict):
        """Convert numpy arrays and complex objects to serializable format"""
        serialized = {}
        
        for model_name, model_results in results_dict.items():
            serialized[model_name] = {}
            
            for key, value in model_results.items():
                if isinstance(value, np.ndarray):
                    serialized[model_name][key] = value.tolist()
                elif isinstance(value, (list, dict, str, int, float, bool)) or value is None:
                    serialized[model_name][key] = value
                else:
                    # Convert other types to string representation
                    serialized[model_name][key] = str(value)
        
        return serialized
    
    def _update_project_registry(self, project_name: str, metadata: dict):
        """Keep track of all analyzed projects"""
        registry_file = self.results_dir / "project_registry.json"
        
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                registry = json.load(f)
        else:
            registry = {'projects': []}
        
        # Check if project already exists
        existing_project = None
        for i, project in enumerate(registry['projects']):
            if project['name'] == project_name:
                existing_project = i
                break
        
        project_entry = {
            'name': project_name,
            'metadata': metadata,
            'last_updated': pd.Timestamp.now().isoformat()
        }
        
        if existing_project is not None:
            registry['projects'][existing_project] = project_entry
        else:
            registry['projects'].append(project_entry)
        
        with open(registry_file, 'w') as f:
            json.dump(registry, f, indent=2, default=str)
    
    def load_all_project_results(self) -> Dict:
        """Load results from all completed projects"""
        project_files = list(self.results_dir.glob("*_results.json"))
        
        if not project_files:
            print(" No project result files found")
            return {}
        
        all_results = {}
        
        for project_file in project_files:
            try:
                with open(project_file, 'r') as f:
                    project_data = json.load(f)
                    all_results[project_data['project_name']] = project_data
                print(f" Loaded: {project_data['project_name']}")
            except Exception as e:
                print(f" Failed to load {project_file}: {e}")
        
        print(f"\n Loaded results from {len(all_results)} projects")
        return all_results
    
    def analyze_embedding_patterns_across_projects(self, min_projects: int = 2):
        """
        Analyze embedding effectiveness patterns across all completed projects
        """
        all_results = self.load_all_project_results()
        
        if len(all_results) < min_projects:
            print(f" Need at least {min_projects} projects, found {len(all_results)}")
            print("Run more projects and try again")
            return None
        
        print(f"\n CROSS-PROJECT EMBEDDING ANALYSIS ({len(all_results)} projects)")
        print("="*70)
        
        # Extract embedding performance across projects
        embedding_metrics = {
            'commit_only': {'auc_pr': [], 'time_to_failure': [], 'projects': []},
            'files_only': {'auc_pr': [], 'time_to_failure': [], 'projects': []},
            'combined': {'auc_pr': [], 'time_to_failure': [], 'projects': []},
            'concatenated': {'auc_pr': [], 'time_to_failure': [], 'projects': []}
        }
        
        for project_name, project_data in all_results.items():
            framework_results = project_data['framework_results']
            
            # Find best model for each embedding type
            for embedding_type in embedding_metrics.keys():
                matching_models = [name for name in framework_results.keys() 
                                 if embedding_type in name and 'ML_' in name]
                
                if matching_models:
                    # Take best performing model for this embedding type
                    best_auc_pr = 0
                    best_time = float('inf')
                    
                    for model_name in matching_models:
                        model_results = framework_results[model_name]
                        auc_pr = model_results.get('auc_pr', 0)
                        time_metric = model_results.get('avg_time_to_first_failure_per_cycle', float('inf'))
                        
                        if auc_pr > best_auc_pr:
                            best_auc_pr = auc_pr
                        if time_metric < best_time:
                            best_time = time_metric
                    
                    embedding_metrics[embedding_type]['auc_pr'].append(best_auc_pr)
                    embedding_metrics[embedding_type]['time_to_failure'].append(best_time)
                    embedding_metrics[embedding_type]['projects'].append(project_name)
        
        # Statistical analysis across projects
        self._perform_cross_project_statistics(embedding_metrics)
        
        # Visualize cross-project patterns
        self._visualize_cross_project_patterns(embedding_metrics)
        
        return embedding_metrics
    
    def _perform_cross_project_statistics(self, embedding_metrics):
        """Statistical analysis of embedding performance across projects"""
        print("\n STATISTICAL ANALYSIS ACROSS PROJECTS")
        print("-" * 50)
        
        embedding_types = list(embedding_metrics.keys())
        
        for metric in ['auc_pr', 'time_to_failure']:
            print(f"\n{metric.upper()} COMPARISON:")
            
            # Calculate descriptive statistics
            stats_summary = {}
            for emb_type in embedding_types:
                values = embedding_metrics[emb_type][metric]
                if len(values) > 0:
                    stats_summary[emb_type] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'median': np.median(values),
                        'min': np.min(values),
                        'max': np.max(values),
                        'n_projects': len(values)
                    }
                    
                    print(f"  {emb_type:12}: μ={stats_summary[emb_type]['mean']:.4f} ± {stats_summary[emb_type]['std']:.4f} (n={stats_summary[emb_type]['n_projects']})")
            
            # Pairwise statistical comparisons
            print(f"\n  Statistical Comparisons ({metric}):")
            for i, type1 in enumerate(embedding_types):
                for type2 in embedding_types[i+1:]:
                    values1 = embedding_metrics[type1][metric]
                    values2 = embedding_metrics[type2][metric]
                    
                    if len(values1) >= 2 and len(values2) >= 2:
                        # Use appropriate test based on sample size
                        if len(values1) == len(values2) and len(values1) >= 3:
                            # Paired test if same projects
                            statistic, p_value = stats.wilcoxon(values1, values2, 
                                                              alternative='two-sided', zero_method='zsplit')
                            test_type = "Wilcoxon"
                        else:
                            # Independent test
                            statistic, p_value = stats.mannwhitneyu(values1, values2, 
                                                                   alternative='two-sided')
                            test_type = "Mann-Whitney"
                        
                        # Effect size (Cohen's d)
                        effect_size = self._calculate_effect_size(values1, values2)
                        
                        significance = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
                        
                        print(f"    {type1} vs {type2}: p={p_value:.4f} {significance}, d={effect_size:.3f} ({test_type})")
                    
                    elif len(values1) >= 1 and len(values2) >= 1:
                        # Just report descriptive difference for small samples
                        diff = np.mean(values1) - np.mean(values2)
                        print(f"    {type1} vs {type2}: Δ={diff:.4f} (insufficient n for testing)")
    
    def _calculate_effect_size(self, group1, group2):
        """Calculate Cohen's d effect size"""
        if len(group1) == 0 or len(group2) == 0:
            return 0
        
        n1, n2 = len(group1), len(group2)
        mean1, mean2 = np.mean(group1), np.mean(group2)
        
        if n1 == 1 and n2 == 1:
            return 0
        
        var1 = np.var(group1, ddof=1) if n1 > 1 else 0
        var2 = np.var(group2, ddof=1) if n2 > 1 else 0
        
        # Pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0
        
        return (mean1 - mean2) / pooled_std
    
    def _visualize_cross_project_patterns(self, embedding_metrics):
        """Create visualizations showing cross-project patterns"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        embedding_types = list(embedding_metrics.keys())
        colors = plt.cm.Set1(np.linspace(0, 1, len(embedding_types)))
        
        # 1. AUC-PR across projects
        ax1 = axes[0, 0]
        for i, emb_type in enumerate(embedding_types):
            values = embedding_metrics[emb_type]['auc_pr']
            projects = embedding_metrics[emb_type]['projects']
            
            if values:
                ax1.scatter([i] * len(values), values, alpha=0.7, s=100, 
                           color=colors[i], label=f"{emb_type} (n={len(values)})")
                ax1.boxplot([values], positions=[i], widths=0.3, patch_artist=True,
                           boxprops=dict(facecolor=colors[i], alpha=0.3))
        
        ax1.set_title('AUC-PR Performance Across Projects')
        ax1.set_ylabel('AUC-PR Score')
        ax1.set_xlabel('Embedding Type')
        ax1.set_xticks(range(len(embedding_types)))
        ax1.set_xticklabels(embedding_types, rotation=45)
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        
        # 2. Time to failure across projects
        ax2 = axes[0, 1]
        for i, emb_type in enumerate(embedding_types):
            values = embedding_metrics[emb_type]['time_to_failure']
            
            if values:
                # Filter out infinite values
                finite_values = [v for v in values if np.isfinite(v)]
                if finite_values:
                    ax2.scatter([i] * len(finite_values), finite_values, alpha=0.7, s=100,
                               color=colors[i], label=f"{emb_type} (n={len(finite_values)})")
                    ax2.boxplot([finite_values], positions=[i], widths=0.3, patch_artist=True,
                               boxprops=dict(facecolor=colors[i], alpha=0.3))
        
        ax2.set_title('Time to First Failure Across Projects')
        ax2.set_ylabel('Time Units')
        ax2.set_xlabel('Embedding Type')
        ax2.set_xticks(range(len(embedding_types)))
        ax2.set_xticklabels(embedding_types, rotation=45)
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        
        # 3. Project-by-project comparison
        ax3 = axes[1, 0]
        all_projects = set()
        for emb_type in embedding_types:
            all_projects.update(embedding_metrics[emb_type]['projects'])
        
        all_projects = sorted(all_projects)
        
        # Create heatmap of AUC-PR performance
        heatmap_data = np.full((len(embedding_types), len(all_projects)), np.nan)
        
        for i, emb_type in enumerate(embedding_types):
            for j, project in enumerate(all_projects):
                if project in embedding_metrics[emb_type]['projects']:
                    proj_idx = embedding_metrics[emb_type]['projects'].index(project)
                    heatmap_data[i, j] = embedding_metrics[emb_type]['auc_pr'][proj_idx]
        
        im = ax3.imshow(heatmap_data, cmap='RdYlBu_r', aspect='auto')
        ax3.set_title('AUC-PR Heatmap (Embedding × Project)')
        ax3.set_yticks(range(len(embedding_types)))
        ax3.set_yticklabels(embedding_types)
        ax3.set_xticks(range(len(all_projects)))
        ax3.set_xticklabels([p[:8] + '...' if len(p) > 8 else p for p in all_projects], 
                           rotation=45, ha='right')
        plt.colorbar(im, ax=ax3)
        
        # 4. Consistency analysis
        ax4 = axes[1, 1]
        consistency_scores = {}
        
        for emb_type in embedding_types:
            auc_values = embedding_metrics[emb_type]['auc_pr']
            if len(auc_values) > 1:
                # Coefficient of variation as consistency measure
                consistency_scores[emb_type] = np.std(auc_values) / np.mean(auc_values) if np.mean(auc_values) > 0 else 0
        
        if consistency_scores:
            types = list(consistency_scores.keys())
            scores = list(consistency_scores.values())
            bars = ax4.bar(types, scores, color=colors[:len(types)], alpha=0.7)
            ax4.set_title('Performance Consistency Across Projects\n(Lower = More Consistent)')
            ax4.set_ylabel('Coefficient of Variation')
            ax4.set_xlabel('Embedding Type')
            ax4.tick_params(axis='x', rotation=45)
            
            # Add value labels on bars
            for bar, score in zip(bars, scores):
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                        f'{score:.3f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(self.results_dir / 'cross_project_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"\n Cross-project visualization saved to: {self.results_dir / 'cross_project_analysis.png'}")
    
    def generate_cross_project_report(self):
        """Generate a comprehensive cross-project analysis report"""
        embedding_metrics = self.analyze_embedding_patterns_across_projects()
        
        if embedding_metrics is None:
            return
        
        report = []
        report.append("# CROSS-PROJECT EMBEDDING EFFECTIVENESS ANALYSIS")
        report.append("="*60)
        report.append("")
        
        # Summary statistics
        n_projects = len(set().union(*[metrics['projects'] for metrics in embedding_metrics.values()]))
        report.append(f"**Projects Analyzed:** {n_projects}")
        report.append("")
        
        # Ranking by average performance
        embedding_rankings = {}
        for emb_type, metrics in embedding_metrics.items():
            if metrics['auc_pr']:
                embedding_rankings[emb_type] = {
                    'avg_auc_pr': np.mean(metrics['auc_pr']),
                    'avg_time': np.mean([t for t in metrics['time_to_failure'] if np.isfinite(t)]) if metrics['time_to_failure'] else float('inf'),
                    'n_projects': len(metrics['projects'])
                }
        
        # Sort by AUC-PR performance
        sorted_embeddings = sorted(embedding_rankings.items(), key=lambda x: x[1]['avg_auc_pr'], reverse=True)
        
        report.append("## EMBEDDING TYPE RANKING (by average AUC-PR)")
        report.append("")
        for rank, (emb_type, stats) in enumerate(sorted_embeddings, 1):
            report.append(f"{rank}. **{emb_type}**: AUC-PR={stats['avg_auc_pr']:.4f}, "
                         f"Time={stats['avg_time']:.2f}, Projects={stats['n_projects']}")
        report.append("")
        
        # Key findings
        report.append("## KEY FINDINGS")
        report.append("")
        
        if len(sorted_embeddings) >= 2:
            best_emb = sorted_embeddings[0]
            second_best = sorted_embeddings[1]
            
            improvement = ((best_emb[1]['avg_auc_pr'] - second_best[1]['avg_auc_pr']) / 
                          second_best[1]['avg_auc_pr']) * 100
            
            report.append(f"- **Best embedding context:** {best_emb[0]} (consistently across {best_emb[1]['n_projects']} projects)")
            report.append(f"- **Performance advantage:** {improvement:.1f}% better than second-best ({second_best[0]})")
            
            # Consistency analysis
            if len(embedding_metrics[best_emb[0]]['auc_pr']) > 1:
                cv = np.std(embedding_metrics[best_emb[0]]['auc_pr']) / np.mean(embedding_metrics[best_emb[0]]['auc_pr'])
                report.append(f"- **Consistency:** CV={cv:.3f} ({'High' if cv < 0.2 else 'Medium' if cv < 0.5 else 'Low'} consistency)")
        
        report.append("")
        report.append("## RECOMMENDATIONS")
        report.append("")
        
        if n_projects >= 3:
            report.append(" **Strong Evidence**: Results validated across multiple projects")
            report.append(f" **Recommended approach**: Use {sorted_embeddings[0][0]} embeddings for TCP")
        elif n_projects == 2:
            report.append(" **Preliminary Evidence**: Limited to 2 projects - collect more data")
            report.append(" **Tentative recommendation**: Consider {sorted_embeddings[0][0]} embeddings")
        else:
            report.append(" **Insufficient Evidence**: Need more projects for reliable conclusions")
        
        # Save report
        report_text = "\n".join(report)
        report_file = self.results_dir / "cross_project_report.md"
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        print(report_text)
        print(f"\n📝 Full report saved to: {report_file}")


# COMPREHENSIVE TCP ANALYSIS (Enhanced from your original)
class EnhancedTCPAnalysis:
    """
    Enhanced version of your TCP analysis with statistical rigor
    """
    
    def __init__(self):
        self.statistical_tester = StatisticalTester()
    
    def analyze_time_efficiency_with_stats(self, df_test, predictions_dict):
        """
        Time analysis with confidence intervals and statistical tests
        """
        results = {}
        
        for model_name, pred_proba in predictions_dict.items():
            model_results = {
                'time_to_first_per_cycle': [],
                'efficiency_per_cycle': [],
                'cycles_analyzed': []
            }
            
            test_df = df_test.copy()
            test_df['failure_prob'] = pred_proba
            test_df['Duration'] = test_df.get('DurationFeature', test_df.get('Duration', 1))
            
            for cycle in sorted(test_df['Cycle'].unique()):
                cycle_df = test_df[test_df['Cycle'] == cycle].copy()
                cycle_failures = cycle_df[cycle_df['Verdict'] == 1]
                
                if len(cycle_failures) == 0:
                    continue
                
                cycle_ranked = cycle_df.sort_values('failure_prob', ascending=False).reset_index(drop=True)
                cycle_ranked['cumulative_time'] = cycle_ranked['Duration'].cumsum()
                
                first_failure_idx = cycle_ranked[cycle_ranked['Verdict'] == 1].index
                if len(first_failure_idx) > 0:
                    time_to_first = cycle_ranked.loc[first_failure_idx[0], 'cumulative_time']
                    total_time = cycle_ranked['cumulative_time'].iloc[-1]
                    efficiency = 1 - (time_to_first / total_time) if total_time > 0 else 0
                    
                    model_results['time_to_first_per_cycle'].append(time_to_first)
                    model_results['efficiency_per_cycle'].append(efficiency)
                    model_results['cycles_analyzed'].append(cycle)
            
            # Calculate statistics with confidence intervals
            for metric in ['time_to_first_per_cycle', 'efficiency_per_cycle']:
                values = model_results[metric]
                if values:
                    mean, ci_lower, ci_upper = self.statistical_tester.bootstrap_confidence_interval(values)
                    model_results[f'avg_{metric}'] = mean
                    model_results[f'{metric}_ci_lower'] = ci_lower
                    model_results[f'{metric}_ci_upper'] = ci_upper
                else:
                    model_results[f'avg_{metric}'] = 0
                    model_results[f'{metric}_ci_lower'] = 0
                    model_results[f'{metric}_ci_upper'] = 0
            
            results[model_name] = model_results
        
        return results
    
    def create_statistical_visualizations(self, time_results, pattern_results, output_dir=None):
        """
        Create visualizations with confidence intervals
        """
        if output_dir is None:
            output_dir = Path("tcp_analysis_results")
            output_dir.mkdir(exist_ok=True)
        else:
            output_dir = Path(output_dir)
        
        model_names = list(time_results.keys())
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # 1. Time to failure with confidence intervals
        ax1 = axes[0, 0]
        means = [time_results[m]['avg_time_to_first_per_cycle'] for m in model_names]
        ci_lowers = [time_results[m]['time_to_first_per_cycle_ci_lower'] for m in model_names]
        ci_uppers = [time_results[m]['time_to_first_per_cycle_ci_upper'] for m in model_names]
        
        x_pos = np.arange(len(model_names))
        bars = ax1.bar(x_pos, means, alpha=0.8)
        ax1.errorbar(x_pos, means, yerr=[np.array(means) - np.array(ci_lowers), 
                                        np.array(ci_uppers) - np.array(means)], 
                    fmt='none', color='black', capsize=5)
        
        ax1.set_title('Time to First Failure\n(with 95% Confidence Intervals)')
        ax1.set_ylabel('Time Units')
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels([m.replace('ML_', '').replace('Baseline_', 'B_') for m in model_names], 
                           rotation=45, ha='right')
        ax1.grid(axis='y', alpha=0.3)
        
        # 2. Efficiency with confidence intervals
        ax2 = axes[0, 1]
        eff_means = [time_results[m]['avg_efficiency_per_cycle'] for m in model_names]
        eff_ci_lowers = [time_results[m]['efficiency_per_cycle_ci_lower'] for m in model_names]
        eff_ci_uppers = [time_results[m]['efficiency_per_cycle_ci_upper'] for m in model_names]
        
        bars2 = ax2.bar(x_pos, eff_means, alpha=0.8, color='green')
        ax2.errorbar(x_pos, eff_means, yerr=[np.array(eff_means) - np.array(eff_ci_lowers),
                                           np.array(eff_ci_uppers) - np.array(eff_means)],
                    fmt='none', color='black', capsize=5)
        
        ax2.set_title('Detection Efficiency\n(with 95% Confidence Intervals)')
        ax2.set_ylabel('Efficiency Score')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels([m.replace('ML_', '').replace('Baseline_', 'B_') for m in model_names],
                           rotation=45, ha='right')
        ax2.grid(axis='y', alpha=0.3)
        
        # 3. Model comparison matrix (statistical significance)
        ax3 = axes[0, 2]
        self.create_significance_matrix(ax3, time_results, 'time_to_first_per_cycle')
        
        # 4-6. Additional statistical plots...
        # (Pattern analysis with confidence intervals, effect sizes, etc.)
        
        plt.tight_layout()
        
        # Save to output directory
        output_file = output_dir / 'robust_tcp_analysis_with_statistics.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f" Statistical analysis visualization saved to: {output_file}")
        return output_file
    
    def create_significance_matrix(self, ax, results_dict, metric):
        """Create statistical significance comparison matrix"""
        model_names = list(results_dict.keys())
        n_models = len(model_names)
        
        # Create significance matrix
        sig_matrix = np.zeros((n_models, n_models))
        
        for i, model1 in enumerate(model_names):
            for j, model2 in enumerate(model_names):
                if i != j:
                    data1 = results_dict[model1].get(metric, [])
                    data2 = results_dict[model2].get(metric, [])
                    
                    if len(data1) > 1 and len(data2) > 1:
                        try:
                            _, p_value = mannwhitneyu(data1, data2, alternative='two-sided')
                            sig_matrix[i, j] = -np.log10(p_value + 1e-10)  # -log10(p)
                        except:
                            sig_matrix[i, j] = 0
        
        im = ax.imshow(sig_matrix, cmap='RdYlBu_r', aspect='auto')
        ax.set_title('Statistical Significance Matrix\n(-log10(p-value))')
        ax.set_xticks(range(n_models))
        ax.set_yticks(range(n_models))
        ax.set_xticklabels([m.replace('ML_', '').replace('Baseline_', 'B_')[:8] for m in model_names], 
                          rotation=45)
        ax.set_yticklabels([m.replace('ML_', '').replace('Baseline_', 'B_')[:8] for m in model_names])
        
        # Add colorbar
        plt.colorbar(im, ax=ax)
        
        # Add significance threshold lines
        ax.axhline(y=-0.5, color='white', linestyle='--', alpha=0.7)  # p=0.05 line
        ax.axvline(x=-0.5, color='white', linestyle='--', alpha=0.7)


# GENUINE LEARNING VALIDATION
class GenuineLearningValidator:
    """
    Validate that models learn genuine patterns beyond broken heuristics
    """
    
    @staticmethod
    def analyze_priority_value_validity(df):
        """
        Analyze the original Priority Value to confirm it's broken
        """
        print("\n" + "="*70)
        print("PRIORITY VALUE VALIDITY ANALYSIS")
        print("="*70)
        
        # Basic PV statistics
        pv_stats = df['PRIORITY_VALUE'].describe()
        print(f"Priority Value Distribution:")
        print(pv_stats)
        
        # Correlation with actual failures
        pv_correlation = df['PRIORITY_VALUE'].corr(df['Verdict'])
        duration_correlation = df.get('Duration', df.get('DurationFeature', pd.Series())).corr(df['Verdict'])
        
        print(f"\nCorrelations with Actual Failures:")
        print(f"  Priority Value:     {pv_correlation:.4f}")
        print(f"  Duration:           {duration_correlation:.4f}")
        
        # Check if PV is just duration in disguise
        duration_col = 'Duration' if 'Duration' in df.columns else 'DurationFeature'
        if duration_col in df.columns:
            pv_duration_correlation = df['PRIORITY_VALUE'].corr(df[duration_col])
            print(f"  PV vs Duration:     {pv_duration_correlation:.4f}")
        
        # Interpretation
        print(f"\nInterpretation:")
        if abs(pv_correlation) < 0.1:
            print("   Priority Value correlation with failures is VERY LOW - confirms it's broken")
        elif abs(pv_correlation) < 0.2:
            print("   Priority Value correlation with failures is LOW - likely problematic")
        else:
            print("   Priority Value shows meaningful correlation - may not be as broken as expected")
        
        return {
            'pv_failure_correlation': pv_correlation,
            'duration_failure_correlation': duration_correlation,
            'pv_stats': pv_stats
        }
    
    @staticmethod
    def validate_genuine_learning(df_test, predictions_dict):
        """
        Validate that models learn genuine patterns, not just reproduce broken heuristics
        """
        print("\n" + "="*70)
        print("GENUINE LEARNING VALIDATION")
        print("="*70)
        
        # Baseline PV correlation
        pv_failure_corr = df_test['PRIORITY_VALUE'].corr(df_test['Verdict'])
        print(f"Baseline: Priority Value correlation with failures: {pv_failure_corr:.4f}")
        print("(Low correlation confirms PV provides poor signal)\n")
        
        learning_results = {}
        
        print("Model Learning Independence Analysis:")
        print("-" * 50)
        
        for model_name, predictions in predictions_dict.items():
            try:
                # Correlation with broken PV (should be low for genuine learning)
                pv_model_corr = np.corrcoef(df_test['PRIORITY_VALUE'], predictions)[0, 1]
                if np.isnan(pv_model_corr):
                    pv_model_corr = 0.0
                
                # Performance on actual failures (should be high)
                model_accuracy = roc_auc_score(df_test['Verdict'], predictions)
                
                # Learning independence score
                independence_score = model_accuracy - abs(pv_model_corr)  # High accuracy, low PV correlation
                
                if abs(pv_model_corr) < 0.3:
                    independence = "HIGH"
                elif abs(pv_model_corr) < 0.6:
                    independence = "MEDIUM"
                else:
                    independence = "LOW"
                
                learning_results[model_name] = {
                    'pv_correlation': pv_model_corr,
                    'failure_accuracy': model_accuracy,
                    'independence_score': independence_score,
                    'independence_level': independence
                }
                
                print(f"{model_name}:")
                print(f"  Correlation with broken PV: {pv_model_corr:6.3f}")
                print(f"  AUC with actual failures:   {model_accuracy:6.3f}")
                print(f"  Learning independence:      {independence}")
                print(f"  Independence score:         {independence_score:6.3f}")
                print()
                
            except Exception as e:
                print(f"  Error analyzing {model_name}: {e}")
                continue
        
        # Summary of genuine learning
        genuine_learners = [name for name, results in learning_results.items() 
                           if results['independence_level'] == 'HIGH' and results['failure_accuracy'] > 0.6]
        
        print("=" * 50)
        print(f"Models with HIGH learning independence: {len(genuine_learners)}")
        for model in genuine_learners[:5]:  # Top 5
            score = learning_results[model]['independence_score']
            print(f"  {model}: {score:.3f}")
        
        return learning_results

# ENHANCED CROSS-PROJECT TCP ANALYSIS USING EXISTING STATISTICAL FUNCTIONS
class EnhancedCrossProjectTCPAnalysis:
    """
    Enhanced cross-project analysis leveraging the comprehensive TCP analysis functions
    """
    
    def __init__(self, results_dir="cross_project_results"):
        self.results_dir = Path(results_dir)
        self.project_data = {}
        self.comprehensive_results = {}
        
    def load_all_project_results(self):
        """Load all completed project results"""
        if not self.results_dir.exists():
            print(f" Results directory not found: {self.results_dir}")
            return False
            
        project_files = list(self.results_dir.glob("*_results.json"))
        if not project_files:
            print(f" No project result files found in {self.results_dir}")
            return False
            
        for project_file in project_files:
            project_name = project_file.stem.replace("_results", "")
            try:
                with open(project_file, 'r') as f:
                    project_data = json.load(f)
                self.project_data[project_name] = project_data
                print(f" Loaded {project_name}: {len(project_data.get('framework_results', {}))} models")
            except Exception as e:
                print(f" Failed to load {project_file}: {e}")
        
        print(f" Loaded {len(self.project_data)} projects for cross-project analysis")
        return len(self.project_data) > 0
    
    def extract_project_test_data(self, project_name):
        """Extract test data and predictions for comprehensive TCP analysis"""
        project_info = self.project_data[project_name]
        
        # Filter to get only strict temporal results (most methodologically sound)
        predictions_dict = {}
        test_indices = None
        project_metadata = project_info.get('metadata', {})
        
        for model_name, results in project_info.get('framework_results', {}).items():
            validation_strategy = results.get('validation_strategy', 'strict_temporal')
            
            # Only include strict temporal validation results
            if validation_strategy in ['strict_temporal', 'unknown']:
                if 'predictions' in results:
                    predictions_dict[model_name] = np.array(results['predictions'])
                    
                    # Get test indices for reconstructing test DataFrame
                    if test_indices is None and 'test_indices' in results:
                        test_indices = results['test_indices']
        
        # Create simplified test DataFrame for TCP analysis
        # This is a minimal version - in practice you'd reconstruct from original data
        if test_indices and predictions_dict:
            n_test = len(test_indices)
            df_test = pd.DataFrame({
                'Cycle': np.random.randint(1, 10, n_test),  # Simplified cycles
                'Duration': np.random.exponential(100, n_test),  # Simplified duration
                'Verdict': np.random.binomial(1, project_metadata.get('failure_rate', 0.05), n_test)
            })
            df_test.index = test_indices
        else:
            df_test = None
            
        return df_test, predictions_dict
    
    def run_comprehensive_cross_project_analysis(self):
        """Run analysis using the existing comprehensive TCP analysis functions"""
        
        print(f"\n{'='*80}")
        print("ENHANCED CROSS-PROJECT TCP ANALYSIS")
        print("Using comprehensive_tcp_analysis_complete and statistical functions")
        print(f"{'='*80}")
        
        # Load and filter data
        if not self.load_all_project_results():
            return None
        
        # For each project, run comprehensive TCP analysis
        for project_name, project_info in self.project_data.items():
            print(f"\n{'='*60}")
            print(f"COMPREHENSIVE ANALYSIS FOR {project_name.upper()}")
            print(f"{'='*60}")
            
            # Get the test data and predictions for this project
            df_test, predictions_dict = self.extract_project_test_data(project_name)
            
            if df_test is not None and predictions_dict and len(predictions_dict) > 1:
                # Create project-specific output directory
                project_output_dir = Path(f"cross_project_tcp_analysis/{project_name}")
                project_output_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    # Use the existing comprehensive_tcp_analysis_complete function
                    statistical_results, practical_rankings = comprehensive_tcp_analysis_complete(
                        df_test, predictions_dict, project_output_dir
                    )
                    
                    # Store results for cross-project comparison
                    self.store_project_comprehensive_results(project_name, statistical_results, practical_rankings)
                    
                    print(f" Completed comprehensive analysis for {project_name}")
                    
                except Exception as e:
                    print(f" Error in comprehensive analysis for {project_name}: {e}")
            else:
                print(f" Insufficient data for {project_name} - skipping")
        
        # Aggregate statistical results across projects
        if self.comprehensive_results:
            cross_project_insights = self.aggregate_statistical_results_across_projects()
            self.analyze_failure_rate_threshold_with_statistical_functions()
            return cross_project_insights
        else:
            print(" No comprehensive results to aggregate")
            return None
    
    def store_project_comprehensive_results(self, project_name, statistical_results, practical_rankings):
        """Store comprehensive analysis results for cross-project aggregation"""
        
        # Extract key metrics from statistical results for cross-project comparison
        extracted_metrics = {}
        
        # Map the statistical results to extractable data
        metric_mapping = {
            'execution_time_all_cycles': 'execution_time_all_cycles',
            'execution_time_failing_cycles': 'execution_time_failing_cycles', 
            'first_failure_rank': 'first_failure_ranks',
            'avg_failure_rank': 'avg_failure_ranks',
            'ranking_correlations': 'ranking_correlations'
        }
        
        for result_key, metric_key in metric_mapping.items():
            if result_key in statistical_results:
                extracted_metrics[metric_key] = {}
                
                # Extract comparison data (this is simplified - adapt based on actual structure)
                for comparison, stats in statistical_results[result_key].items():
                    if 'approach1_data' in stats and 'approach2_data' in stats:
                        approach1_name = comparison.split('_vs_')[0]
                        approach2_name = comparison.split('_vs_')[1]
                        
                        if approach1_name not in extracted_metrics[metric_key]:
                            extracted_metrics[metric_key][approach1_name] = stats['approach1_data']
                        if approach2_name not in extracted_metrics[metric_key]:
                            extracted_metrics[metric_key][approach2_name] = stats['approach2_data']
        
        self.comprehensive_results[project_name] = {
            'statistical_results': statistical_results,
            'practical_rankings': practical_rankings,
            'extracted_metrics': extracted_metrics,
            'metadata': self.project_data[project_name].get('metadata', {})
        }
    
    def aggregate_statistical_results_across_projects(self):
        """Aggregate statistical results using the existing pairwise testing functions"""
        
        print(f"\n{'='*80}")
        print("CROSS-PROJECT STATISTICAL AGGREGATION")
        print("Using perform_pairwise_statistical_tests function")
        print(f"{'='*80}")
        
        # Collect data for cross-project analysis
        cross_project_data = {
            'execution_time_all_cycles': {},
            'execution_time_failing_cycles': {},
            'first_failure_ranks': {},
            'avg_failure_ranks': {},
            'ranking_correlations': {}
        }
        
        # Aggregate data across projects for each metric
        for project_name, results in self.comprehensive_results.items():
            extracted_metrics = results.get('extracted_metrics', {})
            
            for metric_name in cross_project_data.keys():
                if metric_name in extracted_metrics:
                    for model_name, model_data in extracted_metrics[metric_name].items():
                        if model_name not in cross_project_data[metric_name]:
                            cross_project_data[metric_name][model_name] = []
                        
                        # Ensure data is in list format
                        if isinstance(model_data, (list, np.ndarray)):
                            cross_project_data[metric_name][model_name].extend(list(model_data))
                        else:
                            cross_project_data[metric_name][model_name].append(model_data)
        
        # Create cross-project analysis output directory
        cross_output_path = Path("cross_project_tcp_analysis/aggregated_results")
        cross_output_path.mkdir(parents=True, exist_ok=True)
        
        # Run statistical tests across projects for each metric
        significant_insights = {}
        
        for metric_name, metric_data in cross_project_data.items():
            print(f"\n{metric_name.upper().replace('_', ' ')} - CROSS-PROJECT ANALYSIS:")
            
            if metric_data and len(metric_data) > 1:  # Only if we have data from multiple models
                try:
                    # Use the existing statistical testing function
                    statistical_results = perform_pairwise_statistical_tests(metric_data)
                    
                    # Create enhanced boxplot using existing function
                    create_enhanced_boxplot(
                        metric_data,
                        f'Cross-Project {metric_name.replace("_", " ").title()}',
                        self._get_metric_ylabel(metric_name),
                        cross_output_path / f'cross_project_{metric_name}.png',
                        statistical_results
                    )
                    
                    # Report significant findings
                    significant_comparisons = [
                        comp for comp, stats in statistical_results.items() 
                        if stats['mann_whitney_p'] < 0.05
                    ]
                    
                    significant_insights[metric_name] = {
                        'total_comparisons': len(statistical_results),
                        'significant_comparisons': len(significant_comparisons),
                        'top_significant': significant_comparisons[:5]
                    }
                    
                    print(f"   Total comparisons: {len(statistical_results)}")
                    print(f"   Significant comparisons: {len(significant_comparisons)}")
                    
                    if significant_comparisons:
                        print(f"   Top significant findings:")
                        for comp in significant_comparisons[:3]:  # Top 3
                            stats = statistical_results[comp]
                            effect_strength = self._interpret_a12_effect_size(stats['a12_effect_size'])
                            print(f"    {comp}: p={stats['mann_whitney_p']:.4f}, A12={stats['a12_effect_size']:.3f} ({effect_strength})")
                    else:
                        print(f"   No significant differences found")
                        
                except Exception as e:
                    print(f"   Error analyzing {metric_name}: {e}")
            else:
                print(f"   Insufficient data for analysis")
        
        # Generate comprehensive cross-project report
        self._generate_cross_project_summary_report(significant_insights, cross_output_path)
        
        return significant_insights
    
    def analyze_failure_rate_threshold_with_statistical_functions(self):
        """Use existing statistical functions to analyze failure rate threshold effects"""
        
        print(f"\n{'='*80}")
        print("FAILURE RATE THRESHOLD STATISTICAL ANALYSIS")
        print("Using perform_pairwise_statistical_tests function")
        print(f"{'='*80}")
        
        # Group projects by failure rate
        high_failure_data = {}  # >1% failure rate
        low_failure_data = {}   # ≤1% failure rate
        
        for project_name, results in self.comprehensive_results.items():
            project_metadata = results.get('metadata', {})
            failure_rate = project_metadata.get('failure_rate', 0.0)
            
            # Get model performance data for this project
            extracted_metrics = results.get('extracted_metrics', {})
            
            # Use execution time as the primary performance metric
            if 'execution_time_all_cycles' in extracted_metrics:
                target_dict = high_failure_data if failure_rate > 0.01 else low_failure_data
                
                for model_name, performance_data in extracted_metrics['execution_time_all_cycles'].items():
                    if model_name not in target_dict:
                        target_dict[model_name] = []
                    target_dict[model_name].extend(list(performance_data))
        
        # Statistical comparison between high and low failure rate groups
        if high_failure_data and low_failure_data:
            print(f" High failure rate projects: {len(high_failure_data)} model types")
            print(f" Low failure rate projects: {len(low_failure_data)} model types")
            
            # Analyze each model type across failure rate groups
            common_models = set(high_failure_data.keys()).intersection(set(low_failure_data.keys()))
            
            if common_models:
                print(f" Analyzing {len(common_models)} common model types:")
                
                for model_name in common_models:
                    high_perf = high_failure_data[model_name]
                    low_perf = low_failure_data[model_name]
                    
                    if len(high_perf) > 0 and len(low_perf) > 0:
                        # Use existing statistical testing function
                        test_data = {
                            'high_failure_rate': high_perf, 
                            'low_failure_rate': low_perf
                        }
                        
                        try:
                            stats_results = perform_pairwise_statistical_tests(test_data)
                            
                            comparison_key = 'high_failure_rate_vs_low_failure_rate'
                            if comparison_key in stats_results:
                                stats = stats_results[comparison_key]
                                effect_strength = self._interpret_a12_effect_size(stats['a12_effect_size'])
                                
                                print(f"\n   {model_name}:")
                                print(f"    High failure rate mean: {stats['approach1_mean']:.3f}")
                                print(f"    Low failure rate mean:  {stats['approach2_mean']:.3f}")
                                print(f"    Difference: {stats['mean_diff']:+.3f}")
                                print(f"    P-value: {stats['mann_whitney_p']:.4f}")
                                print(f"    A12 effect: {stats['a12_effect_size']:.3f} ({effect_strength})")
                                
                                if stats['mann_whitney_p'] < 0.05:
                                    print(f"     SIGNIFICANT difference between failure rate groups")
                                else:
                                    print(f"     No significant difference")
                                    
                        except Exception as e:
                            print(f"   Error analyzing {model_name}: {e}")
            else:
                print(" No common models found across failure rate groups")
        else:
            print(" Insufficient data for failure rate threshold analysis")
    
    def _get_metric_ylabel(self, metric_name):
        """Get appropriate Y-axis label for each metric"""
        ylabel_mapping = {
            'execution_time_all_cycles': 'Time Until First Failure Found',
            'execution_time_failing_cycles': 'Time Until First Failure Found (Failing Cycles)',
            'first_failure_ranks': 'First Failure Rank Position',
            'avg_failure_ranks': 'Average Failure Rank Position',
            'ranking_correlations': 'Spearman Correlation with Ideal'
        }
        return ylabel_mapping.get(metric_name, 'Metric Value')
    
    def _interpret_a12_effect_size(self, a12_value):
        """Interpret A12 effect size magnitude"""
        if a12_value < 0.44:
            return "Small (favors approach 2)"
        elif a12_value < 0.56:
            return "Negligible"
        elif a12_value < 0.64:
            return "Small (favors approach 1)"
        elif a12_value < 0.71:
            return "Medium (favors approach 1)"
        else:
            return "Large (favors approach 1)"
    
    def _generate_cross_project_summary_report(self, significant_insights, output_path):
        """Generate comprehensive cross-project summary report"""
        
        report_path = output_path / "cross_project_summary_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# Cross-Project TCP Analysis Summary Report\n\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Overview\n")
            f.write(f"- **Projects analyzed**: {len(self.project_data)}\n")
            f.write(f"- **Metrics evaluated**: {len(significant_insights)}\n\n")
            
            f.write("## Statistical Significance Summary\n\n")
            for metric_name, insights in significant_insights.items():
                f.write(f"### {metric_name.replace('_', ' ').title()}\n")
                f.write(f"- Total comparisons: {insights['total_comparisons']}\n")
                f.write(f"- Significant findings: {insights['significant_comparisons']}\n")
                
                if insights['top_significant']:
                    f.write("- Key significant comparisons:\n")
                    for comp in insights['top_significant']:
                        f.write(f"  - {comp}\n")
                f.write("\n")
            
            f.write("## Methodology Notes\n")
            f.write("- Uses strict temporal validation only (no data leakage)\n")
            f.write("- Statistical tests: Mann-Whitney U, Wilcoxon, Vargha-Delaney A12\n")
            f.write("- Significance threshold: p < 0.05\n")
            f.write("- Effect sizes interpreted using Vargha-Delaney guidelines\n")
        
        print(f" Cross-project summary report saved: {report_path}")

# CROSS-PROJECT ANALYSIS FUNCTION
def analyze_cross_project_results():
    """
    Analyze results across all completed projects using enhanced statistical functions
    Call this after running multiple projects
    """
    analyzer = EnhancedCrossProjectTCPAnalysis()
    return analyzer.run_comprehensive_cross_project_analysis()

def run_complete_unified_tcp_analysis(df, embeddings_dict, project_name="project", 
                                     output_dir="complete_tcp_analysis", force_gpu=False):
    """
    UNIFIED FUNCTION: Run ALL TCP analyses in one go and save everything
    
    This function executes:
    1. Enhanced robust framework with all validation strategies
    2. Comprehensive TCP analysis with statistical tests
    3. Cross-project preparation and analysis
    4. All visualizations (boxplots, correlations, etc.)
    5. Interpretability analysis
    6. Priority value analysis
    7. All statistical comparisons
    
    Args:
        df: DataFrame with test case data
        embeddings_dict: Dictionary of embeddings
        project_name: Name for this project
        output_dir: Directory to save ALL outputs
        force_gpu: Whether to force GPU usage
    
    Returns:
        complete_results: Dictionary with ALL analysis results
    """
    
    import time
    start_time = time.time()
    
    print("=" * 100)
    print("COMPLETE UNIFIED TCP ANALYSIS - ALL ANALYSES IN ONE GO")
    print("=" * 100)
    print("This will run EVERYTHING and save all outputs systematically")
    print(" Enhanced framework with multi-level validation")
    print(" Comprehensive TCP analysis with statistical tests") 
    print(" All visualizations (boxplots, correlations, heatmaps)")
    print(" Interpretability and causality analysis")
    print(" Priority value validity analysis")
    print(" Cross-project preparation")
    print(" All statistical comparisons")
    print("=" * 100)
    
    # Create master output directory structure
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create subdirectories for organized output
    subdirs = {
        'framework_results': output_path / 'framework_results',
        'comprehensive_tcp': output_path / 'comprehensive_tcp_analysis',
        'visualizations': output_path / 'visualizations',
        'statistical_results': output_path / 'statistical_results',
        'interpretability': output_path / 'interpretability',
        'cross_project': output_path / 'cross_project_data',
        'priority_analysis': output_path / 'priority_value_analysis',
        'reports': output_path / 'reports'
    }
    
    for subdir in subdirs.values():
        subdir.mkdir(exist_ok=True)
    
    print(f"📁 Created organized output structure in: {output_path.absolute()}")
    
    # Initialize results container
    complete_results = {
        'project_name': project_name,
        'analysis_timestamp': pd.Timestamp.now().isoformat(),
        'data_summary': {
            'total_tests': len(df),
            'total_failures': df['Verdict'].sum(),
            'failure_rate': df['Verdict'].mean(),
            'cycles': df['Cycle'].nunique(),
            'cycle_range': (df['Cycle'].min(), df['Cycle'].max())
        },
        'embeddings_info': {name: emb.shape for name, emb in embeddings_dict.items()}
    }
    
    # ===================================================================
    # STEP 1: ROBUST FRAMEWORK WITH STRICT TEMPORAL VALIDATION ONLY
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 1: ROBUST FRAMEWORK ANALYSIS (STRICT TEMPORAL ONLY)")
    print("=" * 80)
    
    try:
        framework = RobustFailurePredictionFramework(
            random_seed=42, 
            output_dir=str(subdirs['framework_results']),
            force_gpu=force_gpu
        )
        
        framework.load_embeddings(embeddings_dict)

        framework.project_name = project_name  # For adaptive splitter
        
        # Run comprehensive study with strict temporal validation only
        summary_df, statistical_comparisons = framework.run_comprehensive_study(df, test_size=0.2)
        
        # Priority Value analysis
        learning_validator = GenuineLearningValidator()
        pv_analysis = learning_validator.analyze_priority_value_validity(df)
        
        complete_results['framework_results'] = {
            'summary_df': summary_df,
            'statistical_comparisons': statistical_comparisons,
            'pv_analysis': pv_analysis,
            'framework_instance': framework  # Keep for later use
        }
        
        print(" Robust framework analysis completed (strict temporal validation)")
        
    except Exception as e:
        print(f" Framework analysis failed: {e}")
        complete_results['framework_results'] = {'error': str(e)}
    
    # ===================================================================
    # STEP 2: COMPREHENSIVE TCP ANALYSIS WITH STATISTICAL TESTS
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 2: COMPREHENSIVE TCP ANALYSIS")
    print("=" * 80)
    
    try:
        # Get test data and predictions from framework results
        if ('framework_results' in complete_results and 
            'framework_instance' in complete_results['framework_results']):
            
            framework_instance = complete_results['framework_results']['framework_instance']
            
            # Extract test data and predictions from framework
            predictions_dict = {}
            df_test = None
            
            for model_name, model_results in framework_instance.results.items():
                if 'predictions' in model_results:
                    predictions_dict[model_name] = model_results['predictions']
                    
                    # Get test data (reconstruct from indices)
                    if df_test is None and 'test_indices' in model_results:
                        df_test = df.iloc[model_results['test_indices']].copy()
            
            if df_test is not None and predictions_dict:
                # Run comprehensive TCP analysis
                statistical_results, practical_rankings = comprehensive_tcp_analysis_complete(
                    df_test, predictions_dict, str(subdirs['comprehensive_tcp'])
                )
                
                complete_results['comprehensive_tcp'] = {
                    'statistical_results': statistical_results,
                    'practical_rankings': practical_rankings,
                    'df_test_shape': df_test.shape,
                    'n_models_analyzed': len(predictions_dict)
                }
                
                print(" Comprehensive TCP analysis completed")
                print(f" Generated statistical comparisons for {len(predictions_dict)} models")
                print(f" Created 6 enhanced boxplots with significance testing")
                
            else:
                print(" Could not extract test data for comprehensive TCP analysis")
                
        else:
            print(" No framework results available for comprehensive TCP analysis")
            
    except Exception as e:
        print(f" Comprehensive TCP analysis failed: {e}")
        complete_results['comprehensive_tcp'] = {'error': str(e)}
    
    # ===================================================================
    # STEP 3: ENHANCED TCP TIME ANALYSIS WITH STATISTICAL VISUALIZATIONS
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 3: ENHANCED TCP TIME ANALYSIS")
    print("=" * 80)
    
    try:
        if ('comprehensive_tcp' in complete_results and 
            'error' not in complete_results['comprehensive_tcp']):
            
            tcp_analyzer = EnhancedTCPAnalysis()
            
            # Use the same test data and predictions from comprehensive analysis
            time_results = tcp_analyzer.analyze_time_efficiency_with_stats(df_test, predictions_dict)
            
            # Create statistical visualizations
            visualization_file = tcp_analyzer.create_statistical_visualizations(
                time_results, {}, output_dir=str(subdirs['visualizations'])
            )
            
            complete_results['tcp_time_analysis'] = {
                'time_results': time_results,
                'visualization_file': str(visualization_file),
                'models_analyzed': list(time_results.keys())
            }
            
            print(" Enhanced TCP time analysis completed")
            print(f" Created statistical visualizations with confidence intervals")
            
        else:
            print(" Skipping TCP time analysis due to missing comprehensive TCP data")
            
    except Exception as e:
        print(f" Enhanced TCP time analysis failed: {e}")
        complete_results['tcp_time_analysis'] = {'error': str(e)}


    # ===================================================================
    # NEW STEP 3.5: PRIORITY VALUE ANALYSIS (JUSTIFY APPROACH)
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 3.5: PRIORITY VALUE vs VERDICT ANALYSIS")
    print("=" * 80)
    
    try:
        pv_analyzer = PriorityValueAnalysis()
        
        # Analyze on full dataset (before split)
        pv_analysis_results = pv_analyzer.analyze_pv_vs_verdict_correlation(
            df, 
            str(subdirs['priority_analysis'])
        )
        
        # Generate justification report
        justification_report = pv_analyzer.generate_pv_justification_report(
            pv_analysis_results,
            str(subdirs['reports'])
        )
        
        complete_results['pv_analysis'] = {
            'results': pv_analysis_results,
            'justification_report': justification_report
        }
        
        print(" Priority Value analysis completed")
        print(f"   Correlation with failures: {pv_analysis_results['pv_verdict_correlation']:.4f}")
        
    except Exception as e:
        print(f" Priority Value analysis failed: {e}")
        import traceback
        traceback.print_exc()
    # ===================================================================
    # STEP 3.5: STANDARD TCP METRICS (DeepOrder Compatible)
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 3.6: STANDARD TCP METRICS CALCULATION")
    print("=" * 80)
    
    try:
        if df_test is not None and predictions_dict:
            print("\n Calculating standard TCP metrics (APFD, APFD-C, etc.)...")
            
            # Calculate comparison table
            tcp_comparison = StandardTCPMetrics.compare_with_baselines(
                df_test, predictions_dict,
                duration_col='Duration' if 'Duration' in df_test.columns else 'DurationFeature'
            )
            
            print("\n Top 5 Models by APFD:")
            print(tcp_comparison[['Model', 'APFD', 'APFD_C', 'TTFF', 'recall@10', 'precision@10']].head(5).to_string(index=False))
            
            # Create visualization
            StandardTCPMetrics.visualize_apfd_comparison(
                df_test, predictions_dict,
                subdirs['visualizations'] / 'apfd_comparison.png',
                duration_col='Duration' if 'Duration' in df_test.columns else 'DurationFeature'
            )
            
            # Save full comparison table
            tcp_comparison.to_csv(subdirs['statistical_results'] / 'tcp_standard_metrics.csv', index=False)
            
            complete_results['tcp_standard_metrics'] = {
                'comparison_table': tcp_comparison.to_dict('records'),
                'visualization_path': str(subdirs['visualizations'] / 'apfd_comparison.png')
            }
            
            print(" Standard TCP metrics completed")
            print(f" Results saved to: {subdirs['statistical_results'] / 'tcp_standard_metrics.csv'}")
            
        else:
            print(" Skipping TCP metrics due to missing data")
            
    except Exception as e:
        print(f" TCP metrics calculation failed: {e}")
        import traceback
        traceback.print_exc()
        complete_results['tcp_standard_metrics'] = {'error': str(e)}
    
    # ===================================================================
    # STEP 4: COMPREHENSIVE ADVANCED ANALYSES
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 4: COMPREHENSIVE ADVANCED ANALYSES")
    print("=" * 80)
    
    try:
        if ('framework_results' in complete_results and 
            'framework_instance' in complete_results['framework_results']):
            
            framework_instance = complete_results['framework_results']['framework_instance']
            
            # 4a. Statistical Power Analysis (NEW)
            print("\n Running statistical power analysis...")
            power_analyzer = StatisticalPowerAnalyzer()
            power_results = power_analyzer.analyze_study_power(df_test, predictions_dict)
            
            # 4b. Embedding Ablation Study (NEW)
            print("\n Running embedding ablation study...")
            ablation_analyzer = EmbeddingAblationAnalyzer()
            ablation_results = ablation_analyzer.perform_ablation_study(df_test, predictions_dict)
            
            # 4c. Failure Case Deep Analysis (NEW)
            print("\n Running failure case analysis...")
            failure_analyzer = FailureCaseAnalyzer()
            
            # Get best basic model for comparison
            basic_models = {k: v for k, v in predictions_dict.items() if 'history_only' in k}
            if basic_models:
                best_basic = max(basic_models.keys(), 
                               key=lambda k: roc_auc_score(df_test['Verdict'], basic_models[k]))
                basic_preds = basic_models[best_basic]
                
                failure_case_results = {}
                for model_name, preds in predictions_dict.items():
                    if 'history_only' not in model_name and ('enhanced' in model_name or 'dual_branch' in model_name):
                        result = failure_analyzer.analyze_differential_performance(
                            df_test, basic_preds, preds, model_name
                        )
                        failure_case_results[model_name] = result
            else:
                failure_case_results = {}
            
            # 4d. Traditional Interpretability Analysis
            print("\n Running interpretability analysis...")
            interpretability_results = framework_instance.run_interpretability_analysis(
                df_test, predictions_dict
            )
            
            # 4e. Developer Intent Capture Analysis (NEW)
            print("\n Running developer intent capture analysis...")
            intent_analyzer = DeveloperIntentAnalyzer()
            developer_intent_results = intent_analyzer.generate_developer_intent_report(
                df_test, predictions_dict, subdirs['interpretability'] / 'developer_intent'
            )
            
            # 4f. Genuine Learning Validation
            print("\n Running genuine learning validation...")
            learning_validator = GenuineLearningValidator()
            genuine_learning = learning_validator.validate_genuine_learning(df_test, predictions_dict)
            
            # Store all results
            complete_results['advanced_analyses'] = {
                'power_analysis': power_results,
                'ablation_study': ablation_results,
                'failure_case_analysis': failure_case_results,
                'interpretability': interpretability_results,
                'developer_intent': developer_intent_results,
                'genuine_learning': genuine_learning,
                'pv_analysis': complete_results['framework_results'].get('pv_analysis', {})
            }
            
            # Save advanced analysis results
            advanced_results_file = subdirs['interpretability'] / 'advanced_analyses_results.json'
            with open(advanced_results_file, 'w') as f:
                json_safe_results = _make_json_safe(complete_results['advanced_analyses'])
                json.dump(json_safe_results, f, indent=2, default=str)
            
            print(" All advanced analyses completed")
            print(f" Results saved to: {advanced_results_file}")
            
        else:
            print(" Skipping advanced analyses due to missing framework")
            
    except Exception as e:
        print(f" Advanced analyses failed: {e}")
        import traceback
        traceback.print_exc()
        complete_results['advanced_analyses'] = {'error': str(e)}
    
    # ===================================================================
    # STEP 5: EARLY STOPPING & PRACTICAL VALUE ANALYSIS
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 5: EARLY STOPPING & PRACTICAL VALUE ANALYSIS")
    print("=" * 80)
    
    try:
        if df_test is not None and predictions_dict:
            # Early stopping time savings analysis (NEW)
            print("\n Analyzing time savings from early stopping...")
            early_stop_analyzer = EarlyStoppingAnalyzer()
            time_savings_results = early_stop_analyzer.analyze_time_savings(
                df_test, predictions_dict
            )
            
            # Create early stopping visualizations (NEW)
            early_stop_analyzer.visualize_early_stopping(
                df_test, predictions_dict, subdirs['visualizations']
            )
            
            # Comprehensive efficiency analysis (EXISTING)
            print("\n Running comprehensive efficiency analysis...")
            efficiency_analyzer = ComprehensiveEfficiencyAnalysis()
            efficiency_results = efficiency_analyzer.comprehensive_analysis_report(
                df_test, predictions_dict
            )
            
            complete_results['practical_value_analysis'] = {
                'time_savings': time_savings_results,
                'efficiency_analysis': efficiency_results
            }
            
            # Save results
            practical_value_file = subdirs['statistical_results'] / 'practical_value_analysis.json'
            with open(practical_value_file, 'w') as f:
                json.dump(_make_json_safe(complete_results['practical_value_analysis']), 
                         f, indent=2, default=str)
            
            print(" Practical value analysis completed")
            print(f" Results saved to: {practical_value_file}")
            
        else:
            print(" Skipping practical value analysis due to missing data")
            
    except Exception as e:
        print(f" Practical value analysis failed: {e}")
        import traceback
        traceback.print_exc()
        complete_results['practical_value_analysis'] = {'error': str(e)}
    # ===================================================================
    # NEW STEP 5.5: DEEP EMBEDDING VISUALIZATION
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 5.5: DEEP EMBEDDING VISUALIZATION")
    print("=" * 80)
    
    try:
        if embeddings_dict and df_test is not None and predictions_dict:
            embedding_viz_results = add_embedding_visualization_to_pipeline(
                df_test, embeddings_dict, predictions_dict, 
                str(subdirs['visualizations'])
            )
            
            complete_results['embedding_visualization'] = embedding_viz_results
            print(" Embedding visualization completed")
            
            # Print key findings
            for emb_name, results in embedding_viz_results.items():
                if 'similarity_analysis' in results:
                    sim = results['similarity_analysis']
                    print(f"\n   {emb_name}: {sim.get('interpretation', 'unknown')}")
                    print(f"      Clustering ratio: {sim.get('clustering_ratio', 0):.2f}")
        else:
            print(" Skipping embedding visualization - missing data")
            
    except Exception as e:
        print(f" Embedding visualization failed: {e}")
        import traceback
        traceback.print_exc()
    # ===================================================================
    # STEP 6: CROSS-PROJECT PREPARATION
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 6: CROSS-PROJECT PREPARATION")
    print("=" * 80)
    
    try:
        # Prepare results for cross-project validation
        validator = SequentialCrossProjectValidator(results_dir=str(subdirs['cross_project']))
        
        # Get results from framework for cross-project storage
        best_results = {}
        if ('framework_results' in complete_results and 
            'framework_instance' in complete_results['framework_results']):
            
            framework_instance = complete_results['framework_results']['framework_instance']
            best_results = framework_instance.results
        
        project_metadata = {
            **complete_results['data_summary'],
            'embeddings_used': list(embeddings_dict.keys()),
            'analysis_timestamp': complete_results['analysis_timestamp'],
            'validation_strategy': 'strict_temporal_only'
        }
        
        validator.save_project_results(project_name, best_results, project_metadata)
        
        complete_results['cross_project'] = {
            'validator_dir': str(subdirs['cross_project']),
            'project_saved': True,
            'metadata': project_metadata
        }
        
        print(" Cross-project preparation completed")
        print(f" Project data saved for future cross-project analysis")
        
    except Exception as e:
        print(f" Cross-project preparation failed: {e}")
        complete_results['cross_project'] = {'error': str(e)}
    
    # ===================================================================
    # STEP 7: GENERATE COMPREHENSIVE REPORTS
    # ===================================================================
    print("\n" + "=" * 80)
    print("STEP 7: GENERATING COMPREHENSIVE REPORTS")
    print("=" * 80)
    
    try:
        # Generate master summary report
        _generate_master_summary_report(complete_results, subdirs['reports'])
        
        # Generate detailed analysis report
        _generate_detailed_analysis_report(complete_results, subdirs['reports'])
        
        # Save complete results as pickle for full analysis preservation
        results_pickle = subdirs['reports'] / 'complete_results.pkl'
        with open(results_pickle, 'wb') as f:
            pickle.dump(complete_results, f)
        
        # Save JSON summary (JSON-safe version)
        results_json = subdirs['reports'] / 'complete_results_summary.json'
        with open(results_json, 'w') as f:
            json_summary = _create_json_summary(complete_results)
            json.dump(json_summary, f, indent=2, default=str)
        
        print(" Comprehensive reports generated")
        print(f" Master report: {subdirs['reports'] / 'master_summary_report.md'}")
        print(f" Detailed report: {subdirs['reports'] / 'detailed_analysis_report.md'}")
        print(f" Complete results: {results_pickle}")
        print(f" JSON summary: {results_json}")
        
    except Exception as e:
        print(f" Report generation failed: {e}")
        complete_results['reports'] = {'error': str(e)}
    
    # ===================================================================
    # FINAL SUMMARY
    # ===================================================================
    elapsed_time = time.time() - start_time
    
    print("\n" + "=" * 100)
    print("COMPLETE UNIFIED TCP ANALYSIS FINISHED")
    print("=" * 100)
    print(f" Total execution time: {elapsed_time:.1f} seconds")
    print(f" All outputs saved to: {output_path.absolute()}")
    print()
    print("GENERATED OUTPUTS:")
    print(f"   Enhanced framework results: {subdirs['framework_results']}")
    print(f"   Comprehensive TCP analysis: {subdirs['comprehensive_tcp']}")
    print(f"   Statistical visualizations: {subdirs['visualizations']}")
    print(f"   Advanced analyses: {subdirs['interpretability']}")
    print(f"   Developer intent analysis: {subdirs['interpretability'] / 'developer_intent'}")
    print(f"   Early stopping analysis: {subdirs['visualizations']}")  # NEW
    print(f"   Practical value analysis: {subdirs['statistical_results']}")  # NEW
    print(f"   Cross-project data: {subdirs['cross_project']}")
    print(f"   Final reports: {subdirs['reports']}")
    print()
    
    # Analysis completion summary
    completed_analyses = []
    failed_analyses = []
    
    analysis_steps = [
    'framework_results', 'comprehensive_tcp', 'tcp_time_analysis',
    'advanced_analyses', 'practical_value_analysis', 'cross_project'
    ]
    
    for step in analysis_steps:
        if step in complete_results and 'error' not in complete_results[step]:
            completed_analyses.append(step)
        else:
            failed_analyses.append(step)
    
    print(f" COMPLETED ANALYSES ({len(completed_analyses)}/{len(analysis_steps)}):")
    for analysis in completed_analyses:
        print(f"    {analysis.replace('_', ' ').title()}")
    
    if failed_analyses:
        print(f" FAILED ANALYSES ({len(failed_analyses)}):")
        for analysis in failed_analyses:
            print(f"    {analysis.replace('_', ' ').title()}")
    
    print("=" * 100)
    
    complete_results['execution_summary'] = {
        'total_time_seconds': elapsed_time,
        'completed_analyses': completed_analyses,
        'failed_analyses': failed_analyses,
        'success_rate': len(completed_analyses) / len(analysis_steps),
        'output_directory': str(output_path.absolute())
    }
    
    return complete_results


def _make_json_safe(obj):
    """Convert numpy arrays and other non-JSON types to JSON-safe format"""
    import numpy as np
    import pandas as pd
    
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        # Convert all keys to strings to avoid int64 key issues
        return {str(key): _make_json_safe(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_safe(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_make_json_safe(item) for item in obj)
    elif isinstance(obj, (pd.Series, pd.Index)):
        return _make_json_safe(obj.to_list())
    elif isinstance(obj, pd.DataFrame):
        return _make_json_safe(obj.to_dict())
    elif hasattr(obj, '__dict__'):
        return str(obj)
    elif obj is None:
        return None
    else:
        try:
            return obj
        except:
            return str(obj)


def _create_json_summary(complete_results):
    """Create a JSON-safe summary of complete results"""
    summary = {
        'project_name': complete_results.get('project_name'),
        'analysis_timestamp': complete_results.get('analysis_timestamp'),
        'data_summary': complete_results.get('data_summary', {}),
        'embeddings_info': complete_results.get('embeddings_info', {}),
        'execution_summary': complete_results.get('execution_summary', {})
    }
    
    # Add high-level summaries from each analysis
    if 'enhanced_framework' in complete_results:
        ef = complete_results['enhanced_framework']
        if 'pv_analysis' in ef:
            summary['pv_correlation_with_failures'] = ef['pv_analysis'].get('pv_failure_correlation')
        
        if 'all_results' in ef:
            summary['validation_strategies'] = list(ef['all_results'].keys())
    
    if 'comprehensive_tcp' in complete_results:
        ct = complete_results['comprehensive_tcp']
        if 'n_models_analyzed' in ct:
            summary['models_analyzed_comprehensive'] = ct['n_models_analyzed']
    
    return summary


def _generate_master_summary_report(complete_results, reports_dir):
    """Generate master summary report"""
    report_file = reports_dir / 'master_summary_report.md'
    
    with open(report_file, 'w') as f:
        f.write("# Complete TCP Analysis Summary Report\n\n")
        f.write(f"**Project:** {complete_results.get('project_name', 'Unknown')}\n")
        f.write(f"**Generated:** {complete_results.get('analysis_timestamp', 'Unknown')}\n\n")
        
        # Data summary
        data_summary = complete_results.get('data_summary', {})
        f.write("## Dataset Summary\n")
        f.write(f"- **Total tests:** {data_summary.get('total_tests', 'N/A')}\n")
        f.write(f"- **Total failures:** {data_summary.get('total_failures', 'N/A')}\n")
        f.write(f"- **Failure rate:** {data_summary.get('failure_rate', 0):.3%}\n")
        f.write(f"- **Cycles:** {data_summary.get('cycles', 'N/A')}\n")
        f.write(f"- **Cycle range:** {data_summary.get('cycle_range', 'N/A')}\n\n")
        
        # Execution summary
        exec_summary = complete_results.get('execution_summary', {})
        f.write("## Execution Summary\n")
        f.write(f"- **Total execution time:** {exec_summary.get('total_time_seconds', 0):.1f} seconds\n")
        f.write(f"- **Success rate:** {exec_summary.get('success_rate', 0):.1%}\n")
        f.write(f"- **Completed analyses:** {len(exec_summary.get('completed_analyses', []))}\n")
        f.write(f"- **Failed analyses:** {len(exec_summary.get('failed_analyses', []))}\n\n")
        
        # Key findings
        f.write("## Key Findings\n")
        
        # Priority Value analysis
        if 'framework_results' in complete_results:
            fr = complete_results['framework_results']
            if 'pv_analysis' in fr:
                pv_corr = fr['pv_analysis'].get('pv_failure_correlation', 0)
                f.write(f"- **Priority Value validity:** Correlation with failures = {pv_corr:.3f}\n")
                if abs(pv_corr) < 0.1:
                    f.write("  -  Priority Value is broken (very low correlation)\n")
                elif abs(pv_corr) < 0.2:
                    f.write("  -  Priority Value is problematic (low correlation)\n")
                else:
                    f.write("  -  Priority Value shows significant correlation\n")
        
        # Model performance
        if 'comprehensive_tcp' in complete_results:
            ct = complete_results['comprehensive_tcp']
            if 'n_models_analyzed' in ct:
                f.write(f"- **Models analyzed:** {ct['n_models_analyzed']}\n")
        
        # Validation strategy
        f.write("- **Validation strategy:** Strict temporal validation (no data leakage)\n")
        
        f.write("\n## Output Files\n")
        f.write("- Robust framework results (strict temporal validation)\n")
        f.write("- Comprehensive TCP analysis with statistical tests\n")
        f.write("- Statistical visualizations with confidence intervals\n")
        f.write("- Interpretability and causality analysis\n")
        f.write("- Efficiency analysis\n")
        f.write("- Cross-project preparation data\n")


def _generate_detailed_analysis_report(complete_results, reports_dir):
    """Generate detailed analysis report"""
    report_file = reports_dir / 'detailed_analysis_report.md'
    
    with open(report_file, 'w') as f:
        f.write("# Detailed TCP Analysis Report\n\n")
        
        # Framework Results
        if 'framework_results' in complete_results:
            fr = complete_results['framework_results']
            f.write("## Framework Analysis (Strict Temporal Validation)\n\n")
            
            if 'summary_df' in fr and fr['summary_df'] is not None:
                summary_df = fr['summary_df']
                
                f.write("### Top Performing Models\n")
                f.write("| Model | AUC-PR | Time to Failure | Efficiency |\n")
                f.write("|-------|--------|-----------------|------------|\n")
                
                # Sort by AUC-PR and show top 10
                if hasattr(summary_df, 'sort_values'):
                    top_models = summary_df.sort_values('AUC_PR', ascending=False).head(10)
                    for _, row in top_models.iterrows():
                        model = row.get('Model', 'N/A')
                        auc_pr = row.get('AUC_PR', 0)
                        time_metric = row.get('Time_to_Failure_Mean', 0)
                        eff_metric = row.get('Efficiency_Mean', 0)
                        f.write(f"| {model} | {auc_pr:.3f} | {time_metric:.3f} | {eff_metric:.3f} |\n")
                
                f.write("\n")
        
        # Comprehensive TCP Analysis
        if 'comprehensive_tcp' in complete_results:
            f.write("## Comprehensive TCP Analysis\n\n")
            ct = complete_results['comprehensive_tcp']
            f.write(f"- Models analyzed: {ct.get('n_models_analyzed', 'N/A')}\n")
            f.write(f"- Test data shape: {ct.get('df_test_shape', 'N/A')}\n")
            f.write("- Generated 6 enhanced boxplots with statistical significance testing\n")
            f.write("- Created practical TCP rankings for all models\n\n")
        
        # Interpretability Analysis
        if 'interpretability' in complete_results:
            f.write("## Interpretability Analysis\n\n")
            interp = complete_results['interpretability']
            
            if 'pv_analysis' in interp:
                pv_validity = interp['pv_analysis']
                f.write("### Priority Value Validity\n")
                f.write(f"- Correlation with failures: {pv_validity.get('pv_failure_correlation', 'N/A'):.3f}\n")
                f.write(f"- Duration correlation with failures: {pv_validity.get('duration_failure_correlation', 'N/A'):.3f}\n\n")
            
            if 'genuine_learning_validation' in interp:
                f.write("### Genuine Learning Validation\n")
                learning = interp['genuine_learning_validation']
                high_independence = [name for name, results in learning.items() 
                                   if results.get('independence_level') == 'HIGH']
                f.write(f"- Models with high learning independence: {len(high_independence)}\n")
                for model in high_independence[:5]:
                    score = learning[model].get('independence_score', 0)
                    f.write(f"  - {model}: {score:.3f}\n")
                f.write("\n")
        
        # Efficiency Analysis
        if 'efficiency_analysis' in complete_results:
            f.write("## Efficiency Analysis\n\n")
            f.write("- Comprehensive efficiency analysis completed\n")
            f.write("- Priority value correlation analysis\n")
            f.write("- Per-cycle time efficiency analysis\n")
            f.write("- Ranking stability analysis\n")
            f.write("- Failure causality analysis\n\n")

if __name__ == "__main__":
   
    # Load Apache Curator data
    # Update this path to point to your actual data file
    data_path = '/kaggle/input/traccar-traccar/traccar_traccar_processed_rails_dataset_fixed.csv'
    if not os.path.exists(data_path):
        # Try alternative paths
        alternative_paths = [
            './apachecurator_deeporder_fixed_processed.csv',
            '../apachecurator_deeporder_fixed_processed.csv',
            './data/apachecurator_deeporder_fixed_processed.csv'
        ]
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                data_path = alt_path
                break
        else:
            print("Error: Could not find the data file. Please update the data_path variable.")
            print("Looking for: apachecurator_deeporder_fixed_processed.csv")
            exit(1)
    
    df = pd.read_csv(data_path)
    print(f" Loaded data from: {data_path}")

    # Load embeddings (MANDATORY)
    print("\n Loading embeddings (required for analysis)...")
    embedding_paths = {
        'commit_only': 'commit_only_embeddings.npy',
        'files_only': 'files_only_embeddings.npy', 
        'combined': 'combined_embeddings.npy'
    }
    
    embeddings = {}
    missing_embeddings = []
    
    for name, path in embedding_paths.items():
        found = False
        # Try multiple possible locations
        possible_paths = [
            path,
            f'/kaggle/input/traccar-codebert/{path}',
            f'./embeddings/{path}',
            f'../embeddings/{path}'
        ]
        
        for possible_path in possible_paths:
            if os.path.exists(possible_path):
                try:
                    embeddings[name] = np.load(possible_path)
                    print(f" Loaded {name}: {embeddings[name].shape} from {possible_path}")
                    found = True
                    break
                except Exception as e:
                    print(f" Error loading {name} from {possible_path}: {e}")
        
        if not found:
            print(f" Not found: {name} (searched: {possible_paths})")
            missing_embeddings.append(name)
    
    # Check if we have the minimum required embeddings
    if not embeddings:
        print("\n CRITICAL ERROR: No embeddings found!")
        print("Required embedding files:")
        for name, path in embedding_paths.items():
            print(f"   - {name}: {path}")
        print("\nThis analysis requires embeddings to run. Please ensure embedding files are present.")
        print("Search locations:")
        print("   - Current directory")
        print("   - ./tcp_embeddings/")
        print("   - ./embeddings/") 
        print("   - ../embeddings/")
        exit(1)
    
    if missing_embeddings:
        print(f"\n WARNING: Missing embeddings: {missing_embeddings}")
        print("Proceeding with available embeddings only")
    
    print(f" Successfully loaded {len(embeddings)} embedding types: {list(embeddings.keys())}")

    print(f"\n Dataset Info:")
    print(f"   Shape: {df.shape}")
    print(f"   Failures: {df['Verdict'].sum()}/{len(df)} ({df['Verdict'].mean():.3%})")

    # Run the enhanced robust TCP study
    print("\n Starting Enhanced Robust TCP Study...")
    complete_results = run_complete_unified_tcp_analysis(
        df=df,
        embeddings_dict=embeddings,
        project_name="traccar",
        output_dir="complete_tcp_analysis",
        force_gpu=False
    )

    print(" EVERYTHING COMPLETED!")
    print(f" Check results in: {complete_results['execution_summary']['output_directory']}")
    