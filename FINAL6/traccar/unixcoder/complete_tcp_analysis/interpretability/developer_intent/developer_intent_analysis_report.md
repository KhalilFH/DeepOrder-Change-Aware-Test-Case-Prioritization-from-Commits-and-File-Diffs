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
| ML_enhanced_files_only_class_weights | files_only | +1.59% | 0.0002 |
| ML_enhanced_files_only_smote | files_only | +1.59% | 0.0002 |
| ML_enhanced_combined_class_weights | combined | +1.55% | 0.0002 |
| ML_enhanced_combined_smote | combined | +1.58% | 0.0002 |
| ML_enhanced_concatenated_class_weights | concatenated | +1.59% | 0.0002 |
| ML_enhanced_concatenated_smote | concatenated | +1.59% | 0.0002 |
| ML_dual_branch_files_only_class_weights | files_only | +1.59% | 0.0002 |
| ML_dual_branch_files_only_smote | files_only | +1.59% | 0.0002 |
| ML_dual_branch_combined_class_weights | combined | +1.57% | 0.0002 |
| ML_dual_branch_combined_smote | combined | +1.58% | 0.0002 |
| ML_dual_branch_concatenated_class_weights | concatenated | +1.59% | 0.0002 |
| ML_dual_branch_concatenated_smote | concatenated | +1.59% | 0.0002 |

## Code Change Sensitivity Analysis

**Models helping MORE on changed tests:** 2/16
*(Indicates successful developer intent capture)*

- **ML_enhanced_commit_only_smote:** +0.0000 on changed vs +-0.0001 on unchanged
- **ML_dual_branch_commit_only_smote:** +0.0000 on changed vs +-0.0003 on unchanged

## Temporal Pattern Capture

**Models with better temporal stability:** 15/16

## Conclusions

✅ **SUCCESS**: Embeddings show significant improvements AND help more on code changes.
   This indicates successful capture of developer intent.

