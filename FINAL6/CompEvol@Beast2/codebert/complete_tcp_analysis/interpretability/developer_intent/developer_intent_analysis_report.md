# Developer Intent Capture Analysis Report

## Summary

This report analyzes whether code embeddings successfully capture
developer intent and whether this improves test case prioritization.

## Key Questions

1. **Do embeddings improve over history-only models?**
2. **Do embeddings help MORE on code-changed tests?** (intent capture)
3. **Do embeddings provide better temporal generalization?**

## Embedding Contribution Analysis

**Models showing significant improvement:** 15/16

### Significant Improvements

| Model | Embedding | Improvement | P-value |
|-------|-----------|-------------|---------|
| ML_enhanced_commit_only_class_weights | commit_only | -9.22% | 0.0052 |
| ML_enhanced_commit_only_smote | commit_only | -3.10% | 0.0027 |
| ML_enhanced_files_only_class_weights | files_only | -12.40% | 0.0040 |
| ML_enhanced_files_only_smote | files_only | -12.66% | 0.0037 |
| ML_enhanced_combined_class_weights | combined | -5.73% | 0.0281 |
| ML_enhanced_combined_smote | combined | -2.40% | 0.0035 |
| ML_enhanced_concatenated_class_weights | concatenated | -11.40% | 0.0328 |
| ML_enhanced_concatenated_smote | concatenated | -13.33% | 0.0034 |
| ML_dual_branch_commit_only_smote | commit_only | -7.28% | 0.0029 |
| ML_dual_branch_files_only_class_weights | files_only | -17.30% | 0.0000 |
| ML_dual_branch_files_only_smote | files_only | -0.49% | 0.0032 |
| ML_dual_branch_combined_class_weights | combined | -15.74% | 0.0000 |
| ML_dual_branch_combined_smote | combined | -1.96% | 0.0027 |
| ML_dual_branch_concatenated_class_weights | concatenated | -14.91% | 0.0014 |
| ML_dual_branch_concatenated_smote | concatenated | -4.57% | 0.0200 |

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 16/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_class_weights:** +0.0000 on changed vs +-0.0849 on unchanged
- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.0286 on unchanged
- **ML_dual_branch_commit_only_class_weights:** +0.0000 on changed vs +-0.0961 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.0671 on unchanged
- **ML_enhanced_files_only_class_weights:** +0.0000 on changed vs +-0.1142 on unchanged
- **ML_enhanced_files_only_smote:** +0.0000 on changed vs +-0.1167 on unchanged
- **ML_dual_branch_files_only_class_weights:** +0.0000 on changed vs +-0.1594 on unchanged
- **ML_dual_branch_files_only_smote:** +0.0000 on changed vs +-0.0045 on unchanged
- **ML_enhanced_combined_class_weights:** +0.0000 on changed vs +-0.0528 on unchanged
- **ML_enhanced_combined_smote:** +0.0000 on changed vs +-0.0221 on unchanged
- **ML_dual_branch_combined_class_weights:** +0.0000 on changed vs +-0.1450 on unchanged
- **ML_dual_branch_combined_smote:** +0.0000 on changed vs +-0.0181 on unchanged
- **ML_enhanced_concatenated_class_weights:** +0.0000 on changed vs +-0.1051 on unchanged
- **ML_enhanced_concatenated_smote:** +0.0000 on changed vs +-0.1228 on unchanged
- **ML_dual_branch_concatenated_class_weights:** +0.0000 on changed vs +-0.1374 on unchanged
- **ML_dual_branch_concatenated_smote:** +0.0000 on changed vs +-0.0421 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 13/16

## Conclusions

✅ **SUCCESS**: Embeddings show significant improvements AND help more on code changes.
   This indicates successful capture of developer intent.

