# Developer Intent Capture Analysis Report

## Summary

This report analyzes whether code embeddings successfully capture
developer intent and whether this improves test case prioritization.

## Key Questions

1. **Do embeddings improve over history-only models?**
2. **Do embeddings help MORE on code-changed tests?** (intent capture)
3. **Do embeddings provide better temporal generalization?**

## Embedding Contribution Analysis

**Models showing significant improvement:** 0/16

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 13/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_class_weights:** +0.0000 on changed vs +-0.0051 on unchanged
- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.0476 on unchanged
- **ML_dual_branch_commit_only_class_weights:** +0.0000 on changed vs +-0.0062 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.0260 on unchanged
- **ML_enhanced_files_only_class_weights:** +0.0000 on changed vs +-0.0260 on unchanged
- **ML_dual_branch_files_only_class_weights:** +0.0000 on changed vs +-0.0112 on unchanged
- **ML_dual_branch_files_only_smote:** +0.0000 on changed vs +-0.0023 on unchanged
- **ML_enhanced_combined_class_weights:** +0.0000 on changed vs +-0.0481 on unchanged
- **ML_enhanced_combined_smote:** +0.0000 on changed vs +-0.0315 on unchanged
- **ML_dual_branch_combined_class_weights:** +0.0000 on changed vs +-0.0170 on unchanged
- **ML_dual_branch_combined_smote:** +0.0000 on changed vs +-0.0394 on unchanged
- **ML_enhanced_concatenated_class_weights:** +0.0000 on changed vs +-0.0032 on unchanged
- **ML_dual_branch_concatenated_class_weights:** +0.0000 on changed vs +-0.0495 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 3/16

## Conclusions

❌ **LIMITED**: Embeddings show minimal improvements.
   May need better embedding methods or more data.

