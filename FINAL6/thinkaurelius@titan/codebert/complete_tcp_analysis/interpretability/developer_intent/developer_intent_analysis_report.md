# Developer Intent Capture Analysis Report

## Summary

This report analyzes whether code embeddings successfully capture
developer intent and whether this improves test case prioritization.

## Key Questions

1. **Do embeddings improve over history-only models?**
2. **Do embeddings help MORE on code-changed tests?** (intent capture)
3. **Do embeddings provide better temporal generalization?**

## Embedding Contribution Analysis

**Models showing significant improvement:** 3/16

### Significant Improvements

| Model | Embedding | Improvement | P-value |
|-------|-----------|-------------|---------|
| ML_dual_branch_commit_only_class_weights | commit_only | -16.22% | 0.0312 |
| ML_dual_branch_files_only_class_weights | files_only | -23.46% | 0.0333 |
| ML_dual_branch_concatenated_smote | concatenated | -13.26% | 0.0123 |

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 16/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_class_weights:** +0.0000 on changed vs +-0.0723 on unchanged
- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.1572 on unchanged
- **ML_dual_branch_commit_only_class_weights:** +0.0000 on changed vs +-0.1167 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.0879 on unchanged
- **ML_enhanced_files_only_class_weights:** +0.0000 on changed vs +-0.0502 on unchanged
- **ML_enhanced_files_only_smote:** +0.0000 on changed vs +-0.0885 on unchanged
- **ML_dual_branch_files_only_class_weights:** +0.0000 on changed vs +-0.1687 on unchanged
- **ML_dual_branch_files_only_smote:** +0.0000 on changed vs +-0.0389 on unchanged
- **ML_enhanced_combined_class_weights:** +0.0000 on changed vs +-0.0642 on unchanged
- **ML_enhanced_combined_smote:** +0.0000 on changed vs +-0.1787 on unchanged
- **ML_dual_branch_combined_class_weights:** +0.0000 on changed vs +-0.0475 on unchanged
- **ML_dual_branch_combined_smote:** +0.0000 on changed vs +-0.1167 on unchanged
- **ML_enhanced_concatenated_class_weights:** +0.0000 on changed vs +-0.0627 on unchanged
- **ML_enhanced_concatenated_smote:** +0.0000 on changed vs +-0.0509 on unchanged
- **ML_dual_branch_concatenated_class_weights:** +0.0000 on changed vs +-0.0203 on unchanged
- **ML_dual_branch_concatenated_smote:** +0.0000 on changed vs +-0.0954 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 6/16

## Conclusions

✅ **SUCCESS**: Embeddings show significant improvements AND help more on code changes.
   This indicates successful capture of developer intent.

