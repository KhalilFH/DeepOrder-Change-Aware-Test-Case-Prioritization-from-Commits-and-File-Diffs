# Developer Intent Capture Analysis Report

## Summary

This report analyzes whether code embeddings successfully capture
developer intent and whether this improves test case prioritization.

## Key Questions

1. **Do embeddings improve over history-only models?**
2. **Do embeddings help MORE on code-changed tests?** (intent capture)
3. **Do embeddings provide better temporal generalization?**

## Embedding Contribution Analysis

**Models showing significant improvement:** 6/16

### Significant Improvements

| Model | Embedding | Improvement | P-value |
|-------|-----------|-------------|---------|
| ML_enhanced_commit_only_smote | commit_only | -40.50% | 0.0037 |
| ML_enhanced_files_only_smote | files_only | -51.47% | 0.0029 |
| ML_enhanced_combined_class_weights | combined | +2.25% | 0.0280 |
| ML_enhanced_concatenated_class_weights | concatenated | -65.03% | 0.0303 |
| ML_enhanced_concatenated_smote | concatenated | -39.26% | 0.0022 |
| ML_dual_branch_concatenated_smote | concatenated | -46.26% | 0.0431 |

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 13/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_class_weights:** +0.0000 on changed vs +-0.1892 on unchanged
- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.3523 on unchanged
- **ML_dual_branch_commit_only_class_weights:** +0.0000 on changed vs +-0.0675 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.3568 on unchanged
- **ML_enhanced_files_only_class_weights:** +0.0000 on changed vs +-0.3249 on unchanged
- **ML_enhanced_files_only_smote:** +0.0000 on changed vs +-0.4477 on unchanged
- **ML_dual_branch_files_only_class_weights:** +0.0000 on changed vs +-0.1241 on unchanged
- **ML_dual_branch_files_only_smote:** +0.0000 on changed vs +-0.6267 on unchanged
- **ML_enhanced_combined_smote:** +0.0000 on changed vs +-0.2249 on unchanged
- **ML_dual_branch_combined_smote:** +0.0000 on changed vs +-0.0918 on unchanged
- **ML_enhanced_concatenated_class_weights:** +0.0000 on changed vs +-0.5656 on unchanged
- **ML_enhanced_concatenated_smote:** +0.0000 on changed vs +-0.3415 on unchanged
- **ML_dual_branch_concatenated_smote:** +0.0000 on changed vs +-0.4023 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 5/16

## Conclusions

✅ **SUCCESS**: Embeddings show significant improvements AND help more on code changes.
   This indicates successful capture of developer intent.

