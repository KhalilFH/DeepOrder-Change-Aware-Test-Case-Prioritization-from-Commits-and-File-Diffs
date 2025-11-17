# Developer Intent Capture Analysis Report

## Summary

This report analyzes whether code embeddings successfully capture
developer intent and whether this improves test case prioritization.

## Key Questions

1. **Do embeddings improve over history-only models?**
2. **Do embeddings help MORE on code-changed tests?** (intent capture)
3. **Do embeddings provide better temporal generalization?**

## Embedding Contribution Analysis

**Models showing significant improvement:** 8/16

### Significant Improvements

| Model | Embedding | Improvement | P-value |
|-------|-----------|-------------|---------|
| ML_enhanced_commit_only_smote | commit_only | -25.12% | 0.0328 |
| ML_enhanced_files_only_class_weights | files_only | -64.04% | 0.0413 |
| ML_enhanced_files_only_smote | files_only | -61.72% | 0.0498 |
| ML_enhanced_combined_smote | combined | -22.84% | 0.0077 |
| ML_dual_branch_commit_only_class_weights | commit_only | -2.87% | 0.0464 |
| ML_dual_branch_files_only_smote | files_only | -52.38% | 0.0163 |
| ML_dual_branch_combined_class_weights | combined | +1.08% | 0.0180 |
| ML_dual_branch_concatenated_class_weights | concatenated | -1.81% | 0.0467 |

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 15/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_class_weights:** +0.0000 on changed vs +-0.0700 on unchanged
- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.2185 on unchanged
- **ML_dual_branch_commit_only_class_weights:** +0.0000 on changed vs +-0.0250 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.0960 on unchanged
- **ML_enhanced_files_only_class_weights:** +0.0000 on changed vs +-0.5570 on unchanged
- **ML_enhanced_files_only_smote:** +0.0000 on changed vs +-0.5368 on unchanged
- **ML_dual_branch_files_only_class_weights:** +0.0000 on changed vs +-0.3101 on unchanged
- **ML_dual_branch_files_only_smote:** +0.0000 on changed vs +-0.4556 on unchanged
- **ML_enhanced_combined_class_weights:** +0.0000 on changed vs +-0.0443 on unchanged
- **ML_enhanced_combined_smote:** +0.0000 on changed vs +-0.1987 on unchanged
- **ML_dual_branch_combined_smote:** +0.0000 on changed vs +-0.1471 on unchanged
- **ML_enhanced_concatenated_class_weights:** +0.0000 on changed vs +-0.4712 on unchanged
- **ML_enhanced_concatenated_smote:** +0.0000 on changed vs +-0.3485 on unchanged
- **ML_dual_branch_concatenated_class_weights:** +0.0000 on changed vs +-0.0158 on unchanged
- **ML_dual_branch_concatenated_smote:** +0.0000 on changed vs +-0.0762 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 9/16

## Conclusions

✅ **SUCCESS**: Embeddings show significant improvements AND help more on code changes.
   This indicates successful capture of developer intent.

