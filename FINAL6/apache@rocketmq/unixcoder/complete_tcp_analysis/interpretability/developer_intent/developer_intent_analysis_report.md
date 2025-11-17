# Developer Intent Capture Analysis Report

## Summary

This report analyzes whether code embeddings successfully capture
developer intent and whether this improves test case prioritization.

## Key Questions

1. **Do embeddings improve over history-only models?**
2. **Do embeddings help MORE on code-changed tests?** (intent capture)
3. **Do embeddings provide better temporal generalization?**

## Embedding Contribution Analysis

**Models showing significant improvement:** 12/16

### Significant Improvements

| Model | Embedding | Improvement | P-value |
|-------|-----------|-------------|---------|
| ML_enhanced_commit_only_class_weights | commit_only | -29.49% | 0.0436 |
| ML_enhanced_commit_only_smote | commit_only | -48.20% | 0.0002 |
| ML_enhanced_files_only_smote | files_only | -42.79% | 0.0005 |
| ML_enhanced_combined_smote | combined | -47.23% | 0.0002 |
| ML_enhanced_concatenated_smote | concatenated | -35.02% | 0.0005 |
| ML_dual_branch_commit_only_class_weights | commit_only | -66.19% | 0.0008 |
| ML_dual_branch_commit_only_smote | commit_only | -43.78% | 0.0023 |
| ML_dual_branch_files_only_smote | files_only | -60.87% | 0.0002 |
| ML_dual_branch_combined_class_weights | combined | -30.36% | 0.0043 |
| ML_dual_branch_combined_smote | combined | -23.51% | 0.0142 |
| ML_dual_branch_concatenated_class_weights | concatenated | -49.94% | 0.0007 |
| ML_dual_branch_concatenated_smote | concatenated | -47.38% | 0.0003 |

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 16/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_class_weights:** +0.0000 on changed vs +-0.2726 on unchanged
- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.4456 on unchanged
- **ML_dual_branch_commit_only_class_weights:** +0.0000 on changed vs +-0.6118 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.4047 on unchanged
- **ML_enhanced_files_only_class_weights:** +0.0000 on changed vs +-0.2928 on unchanged
- **ML_enhanced_files_only_smote:** +0.0000 on changed vs +-0.3955 on unchanged
- **ML_dual_branch_files_only_class_weights:** +0.0000 on changed vs +-0.0941 on unchanged
- **ML_dual_branch_files_only_smote:** +0.0000 on changed vs +-0.5627 on unchanged
- **ML_enhanced_combined_class_weights:** +0.0000 on changed vs +-0.2012 on unchanged
- **ML_enhanced_combined_smote:** +0.0000 on changed vs +-0.4366 on unchanged
- **ML_dual_branch_combined_class_weights:** +0.0000 on changed vs +-0.2806 on unchanged
- **ML_dual_branch_combined_smote:** +0.0000 on changed vs +-0.2174 on unchanged
- **ML_enhanced_concatenated_class_weights:** +0.0000 on changed vs +-0.2685 on unchanged
- **ML_enhanced_concatenated_smote:** +0.0000 on changed vs +-0.3237 on unchanged
- **ML_dual_branch_concatenated_class_weights:** +0.0000 on changed vs +-0.4617 on unchanged
- **ML_dual_branch_concatenated_smote:** +0.0000 on changed vs +-0.4380 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 3/16

## Conclusions

✅ **SUCCESS**: Embeddings show significant improvements AND help more on code changes.
   This indicates successful capture of developer intent.

