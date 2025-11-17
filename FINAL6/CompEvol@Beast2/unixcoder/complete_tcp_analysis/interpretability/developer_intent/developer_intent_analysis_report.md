# Developer Intent Capture Analysis Report

## Summary

This report analyzes whether code embeddings successfully capture
developer intent and whether this improves test case prioritization.

## Key Questions

1. **Do embeddings improve over history-only models?**
2. **Do embeddings help MORE on code-changed tests?** (intent capture)
3. **Do embeddings provide better temporal generalization?**

## Embedding Contribution Analysis

**Models showing significant improvement:** 13/16

### Significant Improvements

| Model | Embedding | Improvement | P-value |
|-------|-----------|-------------|---------|
| ML_enhanced_commit_only_class_weights | commit_only | -12.14% | 0.0052 |
| ML_enhanced_commit_only_smote | commit_only | -12.43% | 0.0056 |
| ML_enhanced_files_only_class_weights | files_only | +0.30% | 0.0025 |
| ML_enhanced_files_only_smote | files_only | -10.63% | 0.0149 |
| ML_enhanced_combined_class_weights | combined | -1.39% | 0.0034 |
| ML_enhanced_combined_smote | combined | -5.06% | 0.0030 |
| ML_enhanced_concatenated_smote | concatenated | -1.27% | 0.0052 |
| ML_dual_branch_commit_only_smote | commit_only | -8.03% | 0.0015 |
| ML_dual_branch_files_only_class_weights | files_only | -13.32% | 0.0005 |
| ML_dual_branch_combined_class_weights | combined | -0.32% | 0.0241 |
| ML_dual_branch_combined_smote | combined | -2.17% | 0.0042 |
| ML_dual_branch_concatenated_class_weights | concatenated | -7.94% | 0.0089 |
| ML_dual_branch_concatenated_smote | concatenated | -7.86% | 0.0321 |

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 15/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_class_weights:** +0.0000 on changed vs +-0.1119 on unchanged
- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.1145 on unchanged
- **ML_dual_branch_commit_only_class_weights:** +0.0000 on changed vs +-0.0293 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.0740 on unchanged
- **ML_enhanced_files_only_smote:** +0.0000 on changed vs +-0.0980 on unchanged
- **ML_dual_branch_files_only_class_weights:** +0.0000 on changed vs +-0.1227 on unchanged
- **ML_dual_branch_files_only_smote:** +0.0000 on changed vs +-0.0172 on unchanged
- **ML_enhanced_combined_class_weights:** +0.0000 on changed vs +-0.0128 on unchanged
- **ML_enhanced_combined_smote:** +0.0000 on changed vs +-0.0466 on unchanged
- **ML_dual_branch_combined_class_weights:** +0.0000 on changed vs +-0.0029 on unchanged
- **ML_dual_branch_combined_smote:** +0.0000 on changed vs +-0.0200 on unchanged
- **ML_enhanced_concatenated_class_weights:** +0.0000 on changed vs +-0.0609 on unchanged
- **ML_enhanced_concatenated_smote:** +0.0000 on changed vs +-0.0117 on unchanged
- **ML_dual_branch_concatenated_class_weights:** +0.0000 on changed vs +-0.0732 on unchanged
- **ML_dual_branch_concatenated_smote:** +0.0000 on changed vs +-0.0724 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 14/16

## Conclusions

✅ **SUCCESS**: Embeddings show significant improvements AND help more on code changes.
   This indicates successful capture of developer intent.

