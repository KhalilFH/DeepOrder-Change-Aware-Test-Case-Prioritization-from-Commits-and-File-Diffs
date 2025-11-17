import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date

# Step 1: Load your dataset
def load_and_apply_fixed_pipeline(csv_path):
    """
    Load your dataset and apply the fixed DeepOrder preprocessing
    """
    print(f"Loading dataset from: {csv_path}")
    
    # Load your dataset - adjust separator if needed
    df = pd.read_csv(csv_path, sep=",")  # Use sep=';' if semicolon separated
    print(f"Loaded dataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Apply the fixed preprocessing pipeline
    df_processed = complete_deeporder_preprocessing_fixed(df)
    
    return df_processed

# Step 2: The complete fixed pipeline function (copy from previous artifact)
def complete_deeporder_preprocessing_fixed(df_raw):
    """
    Complete fixed DeepOrder preprocessing pipeline from raw data to final features
    Addresses all critical bugs in the original implementation
    """
    print("=== STARTING DEEPORDER PREPROCESSING (FIXED) ===")
    print(f"Initial dataset shape: {df_raw.shape}")
    
    # Step 1: Initial data cleaning and filtering
    print("\n1. Initial data cleaning...")
    
    # Convert boolean Verdict to int if needed
    if df_raw['Verdict'].dtype == bool:
        verdict_mapping = {False: 0, True: 1}
        df_raw['Verdict'] = df_raw['Verdict'].map(verdict_mapping)
    
    print(f"Verdict distribution: {df_raw['Verdict'].value_counts().to_dict()}")
    
    # Step 2: Filter rows with non-empty LastResults
    print("\n2. Filtering non-empty LastResults...")
    print(f"Total rows: {len(df_raw)}")
    
    # Create mask for non-empty LastResults
    mask = df_raw['LastResults'] != '[]'
    print(f"Rows with non-empty LastResults: {mask.sum()}")
    
    df_filtered = df_raw[mask].copy()
    print(f"After filtering empty results: {df_filtered.shape}")
    
    # Step 3: Clean LastResults format
    print("\n3. Cleaning LastResults format...")
    
    # Replace False/True with 0/1 in LastResults
    df_filtered['LastResults'] = df_filtered['LastResults'].str.replace(r'False', '0', regex=True)
    df_filtered['LastResults'] = df_filtered['LastResults'].str.replace(r'True', '1', regex=True)
    
    # Step 4: Filter rows with less than 3 execution history entries
    print("\n4. Filtering execution history (minimum 3 executions)...")
    
    def count_digits_in_results(result_string):
        """Count digits in LastResults string"""
        return len(''.join(x for x in result_string if x.isdigit()))
    
    # Apply digit counting
    digit_counts = df_filtered['LastResults'].apply(count_digits_in_results)
    valid_execution_mask = digit_counts >= 3
    
    df_filtered = df_filtered[valid_execution_mask].reset_index(drop=True)
    print(f"After filtering <3 executions: {df_filtered.shape}")
    
    # Step 5: Extract E1, E2, E3 from LastResults
    print("\n5. Extracting E1, E2, E3 execution history...")
    
    def extract_execution_digits(result_string):
        """Extract first 3 digits from LastResults"""
        digits = ''.join(x for x in result_string if x.isdigit())
        return int(digits[0]), int(digits[1]), int(digits[2])
    
    # Extract execution data
    execution_data = df_filtered['LastResults'].apply(extract_execution_digits)
    df_filtered['E1'] = [x[0] for x in execution_data]
    df_filtered['E2'] = [x[1] for x in execution_data]
    df_filtered['E3'] = [x[2] for x in execution_data]
    
    # Convert to int
    df_filtered['E1'] = df_filtered['E1'].astype(int)
    df_filtered['E2'] = df_filtered['E2'].astype(int)
    df_filtered['E3'] = df_filtered['E3'].astype(int)
    
    print(f"E1, E2, E3 value ranges: {df_filtered[['E1', 'E2', 'E3']].min().min()} to {df_filtered[['E1', 'E2', 'E3']].max().max()}")
    
    # Step 6: FIXED - Calculate distance to last failure
    print("\n6. Calculating distance to last failure (FIXED)...")
    
    def calculate_distance_fixed(row):
        """
        Calculate distance to last failure - FIXED VERSION
        Looking for failures (1) not (-1) as in original buggy code
        """
        # Get execution sequence in reverse chronological order (E3=oldest, E2=middle, E1=most recent)
        sequence = [row['E3'], row['E2'], row['E1']]  # Oldest to newest
        
        # Find position of most recent failure (1 = failure, 0 = pass)
        for i, result in enumerate(sequence):
            if result == 1:  # FIXED: Look for 1 (failure), not -1
                return i + 1
        
        return 0  # No failures found (always successful)
    
    df_filtered['DIST'] = df_filtered.apply(calculate_distance_fixed, axis=1)
    
    print(f"Distance distribution: {df_filtered['DIST'].value_counts().sort_index().to_dict()}")
    no_failure_pct = (df_filtered['DIST'] == 0).mean() * 100
    print(f"Tests with no failures (DIST=0): {no_failure_pct:.1f}%")
    
    # Step 7: Calculate change in status
    print("\n7. Calculating change in status...")
    
    def calculate_change_in_status(row):
        """Count transitions between pass/fail states"""
        sequence = [row['E1'], row['E2'], row['E3']]
        changes = 0
        for i in range(len(sequence) - 1):
            if sequence[i] != sequence[i + 1]:
                changes += 1
        return changes
    
    df_filtered['CHANGE_IN_STATUS'] = df_filtered.apply(calculate_change_in_status, axis=1)
    
    print(f"Change in status distribution: {df_filtered['CHANGE_IN_STATUS'].value_counts().sort_index().to_dict()}")
    
    # Step 7.5: Parse Duration column to numeric values
    print("\n7.5 Parsing Duration column...")
    
    def parse_duration_to_float(duration_str):
        """Convert duration string like '1.23s', '02:13', '1m30s' to float seconds"""
        if isinstance(duration_str, (int, float)):
            return float(duration_str)
        
        if pd.isna(duration_str) or duration_str == '':
            return 0.1
        
        duration_str = str(duration_str).strip()
        
        # Handle MM:SS format like "02:13"
        if ':' in duration_str:
            try:
                parts = duration_str.split(':')
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
                elif len(parts) == 3:  # HH:MM:SS
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = float(parts[2])
                    return hours * 3600 + minutes * 60 + seconds
            except ValueError:
                pass
        
        # Handle formats like "1m30s", "30s", "2m"
        if 'm' in duration_str or 'h' in duration_str:
            total_seconds = 0
            try:
                # Extract hours
                if 'h' in duration_str:
                    h_parts = duration_str.split('h')
                    total_seconds += int(h_parts[0]) * 3600
                    duration_str = h_parts[1] if len(h_parts) > 1 else ''
                
                # Extract minutes
                if 'm' in duration_str:
                    m_parts = duration_str.split('m')
                    total_seconds += int(m_parts[0]) * 60
                    duration_str = m_parts[1] if len(m_parts) > 1 else ''
                
                # Extract seconds
                if 's' in duration_str:
                    duration_str = duration_str.replace('s', '')
                
                if duration_str.strip():
                    total_seconds += float(duration_str.strip())
                
                return total_seconds
            except ValueError:
                pass
        
        # Handle simple formats like '1.23s' or '1.23'
        if duration_str.endswith('s'):
            duration_str = duration_str[:-1]
        
        try:
            return float(duration_str)
        except ValueError:
            print(f"Warning: Could not parse duration '{duration_str}', using 0.1")
            return 0.1  # Default to 100ms
    
    # Parse duration strings to float
    df_filtered['Duration'] = df_filtered['Duration'].apply(parse_duration_to_float)
    print(f"Duration after parsing - min: {df_filtered['Duration'].min()}, max: {df_filtered['Duration'].max()}")
    
    # Step 8: FIXED - Calculate priority values with stable range
    print("\n8. Calculating priority values (FIXED)...")
    
    def calculate_priority_value_fixed(df):
        """
        Calculate priority values with FIXED formula that produces stable range
        """
        # FIXED: Correct weights - recent executions should have higher weight
        weights = np.array([0.7, 0.2, 0.1])  # E1 (recent), E2, E3 (oldest)
        print(f"Using corrected weights: E1={weights[0]}, E2={weights[1]}, E3={weights[2]}")
        
        # Get execution matrix
        MF = df[['E1', 'E2', 'E3']].values
        Te = df['Duration'].values
        
        # Handle zero duration tests
        zero_duration_mask = (Te == 0)
        if zero_duration_mask.any():
            print(f"WARNING: Found {zero_duration_mask.sum()} tests with zero duration - setting to 1ms")
            Te = np.where(Te == 0, 0.001, Te)  # Replace 0 with 1ms
        
        # Calculate weighted failure score
        failure_score = (MF * weights).sum(axis=1)
        print(f"Failure score range: {failure_score.min():.3f} to {failure_score.max():.3f}")
        
        # FIXED: Stable duration component
        # Original buggy formula: priority += max(Te) / Te creates extreme values
        # Fixed formula: Use normalized inverse duration
        
        Te_min, Te_max = Te.min(), Te.max()
        print(f"Duration range: {Te_min} to {Te_max}")
        
        if Te_max > Te_min:
            # Normalize durations to 0-1 range
            Te_normalized = (Te - Te_min) / (Te_max - Te_min)
            # Faster tests get slight bonus (max 0.5 points)
            duration_component = (1 - Te_normalized) * 0.5
        else:
            duration_component = np.zeros_like(Te)
        
        print(f"Duration component range: {duration_component.min():.3f} to {duration_component.max():.3f}")
        
        # Final priority: failure_score (0-3) + duration_component (0-0.5)
        # Total range: 0 to 3.5 (much more stable than original 1.7 to 1.1M)
        priority_value = failure_score + duration_component
        
        print(f"Final priority range: {priority_value.min():.3f} to {priority_value.max():.3f}")
        
        # Handle division by zero for priority range ratio
        if priority_value.min() > 0:
            print(f"Priority range ratio: {priority_value.max() / priority_value.min():.2f}")
        else:
            print(f"Priority range ratio: inf (min value is 0)")
        
        return priority_value
    
    df_filtered['PRIORITY_VALUE'] = calculate_priority_value_fixed(df_filtered)
    
    # Step 9: Process dates and calculate LastRun features
    print("\n9. Processing dates and LastRun features...")
    
    def parse_date_flexible(date_string):
        """Parse date with multiple format support"""
        if pd.isna(date_string) or date_string == '':
            return datetime.now()
        
        date_string = str(date_string).strip()
        
        # List of possible date formats to try
        date_formats = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y %H:%M',
            '%m/%d/%Y',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M',
            '%d/%m/%Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_string, fmt)
            except ValueError:
                continue
        
        # Try to handle the specific error format with remaining data
        # Example: "2025-09-27 19:17:22" but parser expects different format
        try:
            # First try to split and take only the date and time parts we can parse
            if ' ' in date_string:
                date_part, time_part = date_string.split(' ', 1)
                
                # Try date part alone
                try:
                    base_date = datetime.strptime(date_part, '%Y-%m-%d')
                    
                    # Try to parse time part
                    if ':' in time_part:
                        time_components = time_part.split(':')
                        if len(time_components) >= 2:
                            hour = int(time_components[0])
                            minute = int(time_components[1])
                            second = 0
                            
                            # Handle seconds if present
                            if len(time_components) >= 3:
                                # Take only the integer part of seconds (ignore microseconds)
                                second_str = time_components[2].split('.')[0]  
                                if second_str.isdigit():
                                    second = int(second_str)
                            
                            return base_date.replace(hour=hour, minute=minute, second=second)
                    
                    return base_date
                    
                except ValueError:
                    pass
            
            # If all else fails, try to extract just the date part
            date_part = date_string.split()[0]
            return datetime.strptime(date_part, '%Y-%m-%d')
            
        except (ValueError, IndexError):
            # Last resort: return current datetime
            print(f"Warning: Could not parse date '{date_string}', using current time")
            return datetime.now()
    
    # Convert LastRun to datetime - check which column exists
    lastrun_column = None
    for col in ['LastRun', 'LastRunPrevious', 'last_run', 'timestamp']:
        if col in df_filtered.columns:
            lastrun_column = col
            break
    
    if lastrun_column is None:
        print("Warning: No LastRun column found, creating default timestamps")
        # Create default timestamps starting from 30 days ago
        base_time = datetime.now() - timedelta(days=30)
        df_filtered['LastRun_dt'] = [base_time + timedelta(hours=i) for i in range(len(df_filtered))]
    else:
        print(f"Using column '{lastrun_column}' for LastRun data")
        df_filtered['LastRun_dt'] = df_filtered[lastrun_column].apply(parse_date_flexible)
    
    # Adjust dates based on cycle - OPTIMIZED
    print("Adjusting dates by cycle...")
    
    # Calculate cycle differences and add days
    cycle_diffs = df_filtered['Cycle'].values - 1
    
    # Add timedelta days based on cycle
    for i in range(1, len(df_filtered)):  # Start from 1, skip first row
        cycle_diff = int(cycle_diffs[i])
        df_filtered.iloc[i, df_filtered.columns.get_loc('LastRun_dt')] += timedelta(days=cycle_diff)
    
    # Format dates back to string
    df_filtered['LastRun'] = df_filtered['LastRun_dt'].dt.strftime('%Y-%m-%d')
    df_filtered.drop('LastRun_dt', axis=1, inplace=True)
    
    # Step 10: Calculate LastRunFeature (date differences) - OPTIMIZED
    print("\n10. Calculating LastRunFeature (date differences)...")
    
    current_date = date.today()
    
    # Convert all dates at once (vectorized)
    if lastrun_column:
        df_filtered['LastRun_parsed'] = df_filtered[lastrun_column].apply(lambda x: parse_date_flexible(x).date())
    else:
        # Use the LastRun column we just created
        df_filtered['LastRun_parsed'] = pd.to_datetime(df_filtered['LastRun']).dt.date
    
    # Calculate days differences vectorized
    days = []
    prev_date = None
    
    for i in range(len(df_filtered)):
        test_date = df_filtered.iloc[i]['LastRun_parsed']
        
        if i == 0:
            # First test: difference from current date
            delta = current_date - test_date
        else:
            # Subsequent tests: difference from previous test date
            delta = prev_date - test_date
        
        days.append(delta.days)
        prev_date = test_date
    
    df_filtered['LastRunFeature'] = days
    df_filtered.drop('LastRun_parsed', axis=1, inplace=True)
    
    # Step 11: Normalize features globally
    print("\n11. Normalizing features globally...")
    
    # Normalize LastRunFeature to 0-5 range
    lrf_min, lrf_max = df_filtered['LastRunFeature'].min(), df_filtered['LastRunFeature'].max()
    if lrf_max != lrf_min:
        df_filtered['LastRunFeature'] = ((df_filtered['LastRunFeature'] - lrf_min) / (lrf_max - lrf_min)) * 5
        print(f"LastRunFeature normalized: {lrf_min} to {lrf_max} -> 0 to 5")
    else:
        df_filtered['LastRunFeature'] = 2.5  # Constant value
        print(f"LastRunFeature constant, set to 2.5")
    
    # Normalize Duration to DurationFeature (0-5 range)
    dur_min, dur_max = df_filtered['Duration'].min(), df_filtered['Duration'].max()
    if dur_max != dur_min:
        df_filtered['DurationFeature'] = ((df_filtered['Duration'] - dur_min) / (dur_max - dur_min)) * 5
        print(f"Duration normalized: {dur_min} to {dur_max} -> 0 to 5")
    else:
        df_filtered['DurationFeature'] = 2.5  # Constant value
        print(f"Duration constant, set to 2.5")
    
    # Step 12: Final cleanup and preparation
    print("\n12. Final cleanup...")
    
    # Keep Duration as float (don't convert to int since we have fractional seconds)
    df_filtered['Duration'] = df_filtered['Duration'].astype(float)
    
    # Reset Id column
    df_filtered['Id'] = range(1, len(df_filtered) + 1)
    
    # Final validation
    print("\n=== PREPROCESSING VALIDATION ===")
    print(f"Final dataset shape: {df_filtered.shape}")
    print(f"Columns: {list(df_filtered.columns)}")
    
    # Check key feature ranges
    print(f"\nFeature ranges:")
    print(f"  E1, E2, E3: {df_filtered[['E1', 'E2', 'E3']].min().min()} to {df_filtered[['E1', 'E2', 'E3']].max().max()}")
    print(f"  DIST: {df_filtered['DIST'].min()} to {df_filtered['DIST'].max()}")
    print(f"  CHANGE_IN_STATUS: {df_filtered['CHANGE_IN_STATUS'].min()} to {df_filtered['CHANGE_IN_STATUS'].max()}")
    print(f"  PRIORITY_VALUE: {df_filtered['PRIORITY_VALUE'].min():.3f} to {df_filtered['PRIORITY_VALUE'].max():.3f}")
    print(f"  LastRunFeature: {df_filtered['LastRunFeature'].min():.3f} to {df_filtered['LastRunFeature'].max():.3f}")
    print(f"  DurationFeature: {df_filtered['DurationFeature'].min():.3f} to {df_filtered['DurationFeature'].max():.3f}")
    
    # Data quality checks
    print(f"\nData quality:")
    failure_rate = df_filtered['Verdict'].mean()
    print(f"  Failure rate: {failure_rate:.4f} ({failure_rate*100:.2f}%)")
    print(f"  Tests with no failures (DIST=0): {(df_filtered['DIST'] == 0).mean()*100:.1f}%")
    
    # Handle division by zero for priority range ratio
    if df_filtered['PRIORITY_VALUE'].min() > 0:
        print(f"  Priority range ratio: {df_filtered['PRIORITY_VALUE'].max() / df_filtered['PRIORITY_VALUE'].min():.2f}")
    else:
        print(f"  Priority range ratio: inf (min value is 0)")
    
    # Check if suitable for neural networks
    priority_range = df_filtered['PRIORITY_VALUE'].max() - df_filtered['PRIORITY_VALUE'].min()
    if priority_range < 10:
        print("  ✓ Priority value range suitable for neural networks")
    else:
        print("  ⚠ Priority value range may be large for neural networks")
    
    print(f"\n✓ PREPROCESSING COMPLETED SUCCESSFULLY")
    print(f"Ready for DeepOrder training with {len(df_filtered):,} samples")
    
    return df_filtered

# Step 3: Example usage with your specific datasets
if __name__ == "__main__":
    
    # For Rails dataset
    rails_csv_path = "/mnt/c/Users/khali/DeepOrder-Change-Aware-Test-Case-Prioritization-from-Commits-and-File-Diffs/BugSwarm/traccar_traccar_high_failure_19pct_8735.csv"
    
    # For ASE dataset 
    # ase_csv_path = "path/to/your/ase_dataset.csv"
    
    # For GSDTSR dataset
    # gsdtsr_csv_path = "gsdtsr.csv"
    
    print("Processing Rails dataset...")
    try:
        rails_processed = load_and_apply_fixed_pipeline(rails_csv_path)
        
        # Save the processed dataset
        output_path = "traccar_traccar_processed_rails_dataset_fixed.csv"
        rails_processed.to_csv(output_path, index=False)
        print(f"\nProcessed apache  dataset saved to: {output_path}")
        
        # Display sample
        print("\nSample of processed data:")
        print(rails_processed[['E1', 'E2', 'E3', 'DIST', 'CHANGE_IN_STATUS', 'PRIORITY_VALUE', 'Verdict']].head())
        
    except Exception as e:
        print(f"Error processing Rails dataset: {str(e)}")
        print("Check file path and dataset format")
    
    # You can repeat for other datasets:
    # ase_processed = load_and_apply_fixed_pipeline(ase_csv_path)
    # gsdtsr_processed = load_and_apply_fixed_pipeline(gsdtsr_csv_path)