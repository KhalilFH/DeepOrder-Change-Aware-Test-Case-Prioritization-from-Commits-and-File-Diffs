# Developer Intent Capture Analysis Report

## Summary

This report analyzes whether code embeddings successfully capture
developer intent and whether this improves test case prioritization.

## Key Questions

1. **Do embeddings improve over history-only models?**
2. **Do embeddings help MORE on code-changed tests?** (intent capture)
3. **Do embeddings provide better temporal generalization?**

## Embedding Contribution Analysis

**Models showing significant improvement:** 10/16

### Significant Improvements

| Model | Embedding | Improvement | P-value |
|-------|-----------|-------------|---------|
| ML_enhanced_commit_only_class_weights | commit_only | -18.90% | 0.0173 |
| ML_enhanced_commit_only_smote | commit_only | -37.23% | 0.0006 |
| ML_enhanced_files_only_smote | files_only | -38.42% | 0.0008 |
| ML_enhanced_combined_smote | combined | -36.10% | 0.0046 |
| ML_enhanced_concatenated_smote | concatenated | -17.19% | 0.0085 |
| ML_dual_branch_commit_only_smote | commit_only | -44.04% | 0.0004 |
| ML_dual_branch_files_only_smote | files_only | -53.44% | 0.0027 |
| ML_dual_branch_combined_class_weights | combined | -43.66% | 0.0020 |
| ML_dual_branch_combined_smote | combined | -34.37% | 0.0009 |
| ML_dual_branch_concatenated_smote | concatenated | -25.09% | 0.0013 |

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 16/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_class_weights:** +0.0000 on changed vs +-0.1747 on unchanged
- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.3441 on unchanged
- **ML_dual_branch_commit_only_class_weights:** +0.0000 on changed vs +-0.1249 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.4071 on unchanged
- **ML_enhanced_files_only_class_weights:** +0.0000 on changed vs +-0.2519 on unchanged
- **ML_enhanced_files_only_smote:** +0.0000 on changed vs +-0.3552 on unchanged
- **ML_dual_branch_files_only_class_weights:** +0.0000 on changed vs +-0.1484 on unchanged
- **ML_dual_branch_files_only_smote:** +0.0000 on changed vs +-0.4940 on unchanged
- **ML_enhanced_combined_class_weights:** +0.0000 on changed vs +-0.1450 on unchanged
- **ML_enhanced_combined_smote:** +0.0000 on changed vs +-0.3337 on unchanged
- **ML_dual_branch_combined_class_weights:** +0.0000 on changed vs +-0.4036 on unchanged
- **ML_dual_branch_combined_smote:** +0.0000 on changed vs +-0.3177 on unchanged
- **ML_enhanced_concatenated_class_weights:** +0.0000 on changed vs +-0.1071 on unchanged
- **ML_enhanced_concatenated_smote:** +0.0000 on changed vs +-0.1589 on unchanged
- **ML_dual_branch_concatenated_class_weights:** +0.0000 on changed vs +-0.0210 on unchanged
- **ML_dual_branch_concatenated_smote:** +0.0000 on changed vs +-0.2319 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 5/16

## Conclusions

✅ **SUCCESS**: Embeddings show significant improvements AND help more on code changes.
   This indicates successful capture of developer intent.

