# Detailed TCP Analysis Report

## Framework Analysis (Strict Temporal Validation)

### Top Performing Models
| Model | AUC-PR | Time to Failure | Efficiency |
|-------|--------|-----------------|------------|
| ML_dual_branch_concatenated_class_weights | 1.000 | 1.571 | 0.950 |
| ML_enhanced_concatenated_smote | 1.000 | 0.711 | 0.971 |
| ML_enhanced_concatenated_class_weights | 1.000 | 0.954 | 0.971 |
| ML_enhanced_files_only_class_weights | 1.000 | 0.935 | 0.971 |
| ML_enhanced_files_only_smote | 1.000 | 0.910 | 0.971 |
| ML_dual_branch_files_only_class_weights | 1.000 | 1.190 | 0.968 |
| ML_dual_branch_files_only_smote | 1.000 | 0.845 | 0.972 |
| ML_dual_branch_concatenated_smote | 1.000 | 1.247 | 0.967 |
| ML_enhanced_combined_smote | 0.999 | 0.794 | 0.967 |
| ML_dual_branch_combined_smote | 0.999 | 1.196 | 0.949 |

## Comprehensive TCP Analysis

- Models analyzed: 23
- Test data shape: (5468, 24)
- Generated 6 enhanced boxplots with statistical significance testing
- Created practical TCP rankings for all models

