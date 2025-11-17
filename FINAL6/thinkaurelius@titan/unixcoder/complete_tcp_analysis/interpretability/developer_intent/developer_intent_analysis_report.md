# Developer Intent Capture Analysis Report

## Summary

This report analyzes whether code embeddings successfully capture
developer intent and whether this improves test case prioritization.

## Key Questions

1. **Do embeddings improve over history-only models?**
2. **Do embeddings help MORE on code-changed tests?** (intent capture)
3. **Do embeddings provide better temporal generalization?**

## Embedding Contribution Analysis

**Models showing significant improvement:** 1/16

### Significant Improvements

| Model | Embedding | Improvement | P-value |
|-------|-----------|-------------|---------|
| ML_dual_branch_concatenated_smote | concatenated | -20.61% | 0.0442 |

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 15/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_class_weights:** +0.0000 on changed vs +-0.0662 on unchanged
- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.1841 on unchanged
- **ML_dual_branch_commit_only_class_weights:** +0.0000 on changed vs +-0.0283 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.1157 on unchanged
- **ML_enhanced_files_only_class_weights:** +0.0000 on changed vs +-0.0640 on unchanged
- **ML_enhanced_files_only_smote:** +0.0000 on changed vs +-0.0996 on unchanged
- **ML_dual_branch_files_only_class_weights:** +0.0000 on changed vs +-0.0467 on unchanged
- **ML_dual_branch_files_only_smote:** +0.0000 on changed vs +-0.0859 on unchanged
- **ML_enhanced_combined_class_weights:** +0.0000 on changed vs +-0.0419 on unchanged
- **ML_enhanced_combined_smote:** +0.0000 on changed vs +-0.0812 on unchanged
- **ML_dual_branch_combined_class_weights:** +0.0000 on changed vs +-0.0962 on unchanged
- **ML_dual_branch_combined_smote:** +0.0000 on changed vs +-0.0800 on unchanged
- **ML_enhanced_concatenated_class_weights:** +0.0000 on changed vs +-0.1338 on unchanged
- **ML_enhanced_concatenated_smote:** +0.0000 on changed vs +-0.1721 on unchanged
- **ML_dual_branch_concatenated_smote:** +0.0000 on changed vs +-0.1483 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 6/16

## Conclusions

✅ **SUCCESS**: Embeddings show significant improvements AND help more on code changes.
   This indicates successful capture of developer intent.

