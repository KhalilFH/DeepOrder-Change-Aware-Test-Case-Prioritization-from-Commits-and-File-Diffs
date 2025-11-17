#!/usr/bin/env python3
"""
Enhanced TCP-CI Dataset Generator
Creates test case prioritization datasets with improved data integration.

Integrates data from:
1. datasets/ - Main CI/test execution data
2. travis-torrent/ - Additional build and commit information
3. rtp-torrent/ - Test names and execution details

Output Format:
- Id: Unique numeric identifier of the test execution
- Name: Test case name (from rtp-torrent if available, otherwise derived)
- Duration: Test runtime in milliseconds
- CalcPrio: Priority of the test case (fixed to 0 as requested)
- LastRun: Previous execution timestamp (YYYY-MM-DD HH:mm)
- LastResults: List of previous test results [1=Failed, 0=Passed]
- Verdict: Test verdict (1=Failed, 0=Passed)
- Cycle: CI cycle number
- CommitMsg: Commit messages and hashes
- FilesChanged: Files changed in the commit
- BuildStartedAt: Build start timestamp
- LocAdded: Lines of code added in build commits
- LocDeleted: Lines of code deleted in build commits
"""

import pandas as pd
import os
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse


class EnhancedTCPDatasetGenerator:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.datasets_path = self.base_path / "datasets"
        self.travis_torrent_path = self.base_path / "travis-torrent" / "data"
        self.rtp_torrent_path = self.base_path / "rtp-torrent"
        
    def get_available_projects(self) -> List[str]:
        """Get list of all available projects."""
        projects = []
        if self.datasets_path.exists():
            projects = [d.name for d in self.datasets_path.iterdir() if d.is_dir()]
        return sorted(projects)
    
    def load_project_data(self, project_name: str) -> Dict[str, pd.DataFrame]:
        """Load all relevant data files for a project."""
        data = {}
        
        # Load main dataset files
        project_path = self.datasets_path / project_name
        main_files = {
            'exe': 'exe.csv',
            'builds': 'builds.csv', 
            'id_map': 'id_map.csv',
            'entity_history': 'entity_change_history.csv'
        }
        
        for key, filename in main_files.items():
            file_path = project_path / filename
            if file_path.exists():
                try:
                    data[key] = pd.read_csv(file_path)
                    print(f"✓ Loaded {filename}: {len(data[key])} records")
                except Exception as e:
                    print(f"✗ Error loading {filename}: {e}")
        
        # Load travis-torrent data
        travis_path = self.travis_torrent_path / project_name / "data.csv"
        if travis_path.exists():
            try:
                data['travis_builds'] = pd.read_csv(travis_path)
                print(f"✓ Loaded travis-torrent data: {len(data['travis_builds'])} builds")
            except Exception as e:
                print(f"✗ Error loading travis-torrent data: {e}")
        
        # Load rtp-torrent data (contains actual test names)
        rtp_path = self.rtp_torrent_path / project_name
        if rtp_path.exists():
            full_file = rtp_path / f"{project_name}-full.csv"
            if full_file.exists():
                try:
                    data['rtp_tests'] = pd.read_csv(full_file)
                    print(f"✓ Loaded rtp-torrent test data: {len(data['rtp_tests'])} test records")
                except Exception as e:
                    print(f"✗ Error loading rtp-torrent data: {e}")
        
        return data
    
    def load_id_mapping(self, project_path: Path) -> Dict[int, str]:
        """Load the entity ID to file path mapping"""
        id_map_path = project_path / 'id_map.csv'
        if id_map_path.exists():
            try:
                # Read id_map.csv with key,value format where key=filepath, value=entity_id
                id_map_df = pd.read_csv(id_map_path)
                # Create mapping from entity_id (value) to filepath (key)
                return dict(zip(id_map_df['value'], id_map_df['key']))
            except Exception as e:
                print(f"Error loading id_map: {e}")
                return {}
        return {}
    
    def create_test_name_mapping(self, exe_df: pd.DataFrame, rtp_tests_df: Optional[pd.DataFrame],
                                id_map_df: Optional[pd.DataFrame]) -> Dict[int, str]:
        """Create mapping from test IDs to human-readable test names."""
        test_name_map = {}
        
        # Get all unique test IDs from executions
        test_ids = exe_df['test'].unique()
        
        # Try to map using RTP-torrent data first (has actual test names)
        if rtp_tests_df is not None and 'testName' in rtp_tests_df.columns:
            # Create mapping based on order or available patterns
            unique_test_names = rtp_tests_df['testName'].unique()
            print(f"Found {len(unique_test_names)} unique test names in RTP data")
            
            # For now, use a simple approach - if we have fewer unique names than IDs,
            # we'll map by position or use patterns
            for i, test_id in enumerate(sorted(test_ids)):
                if i < len(unique_test_names):
                    test_name_map[test_id] = unique_test_names[i]
                else:
                    test_name_map[test_id] = f"test_{test_id}"
        
        # Fallback to id_map or generic names
        for test_id in test_ids:
            if test_id not in test_name_map:
                if id_map_df is not None and not id_map_df.empty:
                    # Try to find in id_map
                    mapping = id_map_df[id_map_df['key'] == str(test_id)]
                    if not mapping.empty:
                        test_name_map[test_id] = mapping.iloc[0]['value']
                    else:
                        test_name_map[test_id] = f"test_{test_id}"
                else:
                    test_name_map[test_id] = f"test_{test_id}"
        
        return test_name_map
    
    def enhance_build_info_with_travis(self, builds_df: pd.DataFrame, 
                                     travis_builds_df: Optional[pd.DataFrame],
                                     entity_history_df: Optional[pd.DataFrame],
                                     project_name: str) -> Dict:
        """Enhanced build information using travis-torrent data and git extraction."""
        build_info = {}
        
        # Create Travis build mapping if available
        travis_map = {}
        if travis_builds_df is not None:
            for _, row in travis_builds_df.iterrows():
                travis_map[row['tr_build_id']] = {
                    'commit': row['git_all_built_commits'],
                    'timestamp': row['gh_build_started_at']
                }
        
        for _, build in builds_df.iterrows():
            build_id = build['id']
            commits_str = build['commits']
            started_at = build['started_at']
            
            # Extract actual commit messages and file changes
            commit_messages = []
            files_changed_from_git = []
            entity_files_changed = set()
            actual_commit_hashes = []
            
            # Check if this build is in travis data first
            if build_id in travis_map:
                travis_info = travis_map[build_id]
                commits_str = travis_info['commit']
                # Parse multiple commits from travis data (separated by #)
                if pd.notna(commits_str) and commits_str:
                    if '#' in str(commits_str):
                        actual_commit_hashes = [c.strip() for c in str(commits_str).split('#')]
                    else:
                        actual_commit_hashes = [str(commits_str).strip()]
            else:
                # Parse commit hashes from builds.csv
                if pd.notna(commits_str):
                    if '#' in str(commits_str):
                        actual_commit_hashes = [c.strip() for c in str(commits_str).split('#')]
                    else:
                        actual_commit_hashes = [str(commits_str).strip()]
            
            # For each commit, get actual message from git and files from both git and entity history
            for commit_hash in actual_commit_hashes:
                if commit_hash:
                    # Get actual commit message from git
                    commit_msg = self.get_commit_message_from_git(project_name, commit_hash)
                    commit_messages.append(commit_msg)
                    
                    # Get changed files from git (more accurate)
                    git_files = self.get_changed_files_from_git(project_name, commit_hash)
                    files_changed_from_git.extend(git_files)
                    
                    # Also get entity IDs from entity history for backup
                    if entity_history_df is not None and not entity_history_df.empty:
                        commit_changes = entity_history_df[
                            entity_history_df['Commit'] == commit_hash
                        ]
                        if not commit_changes.empty:
                            entity_ids = commit_changes['EntityId'].unique()
                            entity_files_changed.update([int(eid) for eid in entity_ids])
            
            # Fallback if no commit messages found
            if not commit_messages:
                commit_messages = [f"Build {build_id}"]
            
            # Calculate LOC metrics for this build
            loc_metrics = self.get_build_loc_metrics(actual_commit_hashes, project_name)
            
            # Prefer git files over entity files, but use entity files as backup
            final_files_changed = files_changed_from_git if files_changed_from_git else list(entity_files_changed)
            
            build_info[build_id] = {
                'started_at': started_at,
                'commit_messages': '; '.join(commit_messages),
                'files_changed_git': files_changed_from_git,  # Files from git
                'files_changed_entities': list(entity_files_changed),  # Files from entity mapping
                'commit_hashes': actual_commit_hashes,
                'loc_added': loc_metrics['loc_added'],
                'loc_deleted': loc_metrics['loc_deleted'],
                'net_loc_change': loc_metrics['net_loc_change']
            }
        
        return build_info
    
    def get_commit_message_from_git(self, project_name: str, commit_hash: str) -> str:
        """Extract commit message from git repository."""
        try:
            # Path to the project's git repository
            git_repo_path = self.datasets_path / project_name / project_name.split('@')[1]
            
            if not git_repo_path.exists():
                # Try alternative naming
                git_repo_path = self.datasets_path / project_name / project_name.split('@')[0]
            
            if not git_repo_path.exists() or not (git_repo_path / '.git').exists():
                return f"Commit {commit_hash[:8]}"
            
            # Run git command to get commit message
            result = subprocess.run(
                ['git', 'show', '--format=%s', '--no-patch', commit_hash],
                cwd=git_repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                message = result.stdout.strip()
                return message
            else:
                return f"Commit {commit_hash[:8]}"
                
        except Exception as e:
            return f"Commit {commit_hash[:8]}"
    
    def get_changed_files_from_git(self, project_name: str, commit_hash: str) -> List[str]:
        """Extract changed files from git repository."""
        try:
            # Path to the project's git repository
            git_repo_path = self.datasets_path / project_name / project_name.split('@')[1]
            
            if not git_repo_path.exists():
                # Try alternative naming
                git_repo_path = self.datasets_path / project_name / project_name.split('@')[0]
            
            if not git_repo_path.exists() or not (git_repo_path / '.git').exists():
                return []
            
            # Run git command to get changed files
            result = subprocess.run(
                ['git', 'show', '--name-only', '--format=', commit_hash],
                cwd=git_repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
                return files
            else:
                return []
                
        except Exception as e:
            return []
    
    def get_build_loc_metrics(self, commit_hashes: List[str], project_name: str) -> Dict:
        """Calculate aggregated LOC metrics for all commits in a build."""
        total_added = 0
        total_deleted = 0
        files_with_changes = 0
        
        try:
            # Path to the project's git repository
            git_repo_path = self.datasets_path / project_name / project_name.split('@')[1]
            
            if not git_repo_path.exists():
                # Try alternative naming
                git_repo_path = self.datasets_path / project_name / project_name.split('@')[0]
            
            if not git_repo_path.exists() or not (git_repo_path / '.git').exists():
                return {'loc_added': 0, 'loc_deleted': 0, 'net_loc_change': 0}
            
            for commit_hash in commit_hashes:
                if not commit_hash:
                    continue
                    
                # Get numstat for this commit (shows lines added/deleted per file)
                result = subprocess.run(
                    ['git', 'show', '--numstat', '--format=', commit_hash],
                    cwd=git_repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        if line and '\t' in line:
                            parts = line.split('\t')
                            if len(parts) >= 3:  # added, deleted, filename
                                try:
                                    # Handle binary files (marked with '-')
                                    added_str = parts[0].strip()
                                    deleted_str = parts[1].strip()
                                    
                                    if added_str.isdigit() and deleted_str.isdigit():
                                        added = int(added_str)
                                        deleted = int(deleted_str)
                                        total_added += added
                                        total_deleted += deleted
                                        files_with_changes += 1
                                except (ValueError, IndexError):
                                    continue
                                    
        except Exception as e:
            # Return zero metrics on any error
            pass
        
        return {
            'loc_added': total_added,
            'loc_deleted': total_deleted,
            'net_loc_change': total_added - total_deleted
        }
    
    def get_file_names_from_entities(self, entity_ids: List[int], 
                                   id_map_df: Optional[pd.DataFrame]) -> List[str]:
        """Convert entity IDs to actual file names using id_map."""
        file_names = []
        if id_map_df is not None and not id_map_df.empty:
            for entity_id in entity_ids:
                entity_id = int(entity_id)  # Ensure it's a Python int, not numpy.int64
                # The key in id_map corresponds to entity IDs
                mapping = id_map_df[id_map_df.index == entity_id]
                if not mapping.empty:
                    file_names.append(str(mapping.iloc[0]['value']))
                else:
                    # Try string matching with the key column
                    str_mapping = id_map_df[id_map_df['key'] == str(entity_id)]
                    if not str_mapping.empty:
                        file_names.append(str(str_mapping.iloc[0]['value']))
                    else:
                        file_names.append(f"entity_{entity_id}")
        else:
            file_names = [f"entity_{int(eid)}" for eid in entity_ids]
        
        return file_names
    
    def build_test_history(self, exe_df: pd.DataFrame, builds_df: pd.DataFrame) -> Dict:
        """Build execution history for each test."""
        # Sort executions by build start time
        exe_with_builds = exe_df.merge(builds_df[['id', 'started_at']], 
                                      left_on='build', right_on='id', how='left')
        exe_with_builds['started_at'] = pd.to_datetime(exe_with_builds['started_at'])
        exe_with_builds = exe_with_builds.sort_values(['test', 'started_at'])
        
        test_history = {}
        
        for test_id in exe_with_builds['test'].unique():
            test_executions = exe_with_builds[exe_with_builds['test'] == test_id]
            
            history = []
            for _, execution in test_executions.iterrows():
                history.append({
                    'build_id': execution['build'],
                    'verdict': execution['verdict'],
                    'duration': execution['duration'],
                    'started_at': execution['started_at']
                })
            
            test_history[test_id] = history
        
        return test_history
    
    def generate_dataset(self, project_name: str, output_file: Optional[str] = None) -> pd.DataFrame:
        """Generate enhanced TCP dataset for a specific project."""
        print(f"\n=== Generating Enhanced TCP Dataset for {project_name} ===")
        
        # Load all available data
        data = self.load_project_data(project_name)
        
        if 'exe' not in data or 'builds' not in data:
            raise ValueError(f"Missing required files for project {project_name}")
        
        exe_df = data['exe']
        builds_df = data['builds']
        id_map_df = data.get('id_map')
        entity_history_df = data.get('entity_history')
        travis_builds_df = data.get('travis_builds')
        rtp_tests_df = data.get('rtp_tests')
        
        # Load entity ID to filepath mapping
        id_mapping = self.load_id_mapping(self.datasets_path / project_name)
        print(f"Loaded {len(id_mapping)} entity ID to filepath mappings")
        
        print(f"Processing {len(exe_df)} test executions across {len(builds_df)} builds...")
        
        # Check verdict distribution
        verdict_counts = exe_df['verdict'].value_counts().sort_index()
        print(f"Verdict distribution: {dict(verdict_counts)}")
        
        # Create test name mapping using available data sources
        test_name_map = self.create_test_name_mapping(exe_df, rtp_tests_df, id_map_df)
        print(f"Created test name mappings for {len(test_name_map)} tests")
        
        # Enhanced build information
        build_info = self.enhance_build_info_with_travis(builds_df, travis_builds_df, entity_history_df, project_name)
        
        # Build test execution history
        test_history = self.build_test_history(exe_df, builds_df)
        
        # Generate output dataset
        output_records = []
        
        # Add cycle numbers to builds (sorted by date)
        builds_df['started_at'] = pd.to_datetime(builds_df['started_at'])
        builds_df = builds_df.sort_values('started_at')
        build_to_cycle = {row['id']: idx + 1 for idx, (_, row) in enumerate(builds_df.iterrows())}
        
        for _, execution in exe_df.iterrows():
            test_id = execution['test']
            build_id = execution['build']
            
            # Get test history up to this execution
            history = test_history.get(test_id, [])
            current_idx = next((i for i, h in enumerate(history) if h['build_id'] == build_id), -1)
            
            # Previous executions (for LastRun and LastResults)
            prev_executions = history[:current_idx] if current_idx > 0 else []
            
            # Skip tests that don't have previous executions (no LastRun)
            if not prev_executions:
                continue
            
            # LastRun: previous execution timestamp (YYYY-MM-DD HH:MM:SS format)
            last_run = ""
            if prev_executions:
                last_exec = prev_executions[-1]
                if pd.notna(last_exec['started_at']):
                    # Format without timezone
                    last_run = last_exec['started_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            # LastResults: list of previous verdicts (most recent first)
            # Map verdict values: 0=Pass, 1=Fail, 2=Error/Skip -> treat as Fail
            last_results = []
            if prev_executions:
                # Take up to last 10 results, most recent first
                recent_results = []
                for e in prev_executions[-10:]:
                    verdict = int(e['verdict'])
                    # Map verdict 2 to 1 (treat errors/skips as failures)
                    if verdict == 2:
                        verdict = 1
                    recent_results.append(str(verdict))
                last_results = recent_results[::-1]  # Reverse to get most recent first
            
            # Get file names for changed files that triggered the CI cycle
            build_data = build_info.get(build_id, {})
            
            # Prefer git files over entity files
            files_changed_git = build_data.get('files_changed_git', [])
            files_changed_entities = build_data.get('files_changed_entities', [])
            
            if files_changed_git:
                # Use git files directly (they're already file paths)
                file_paths = files_changed_git[:5]  # Limit to first 5
            else:
                # Fallback to entity files (need mapping to actual file paths)
                entity_ids = files_changed_entities[:5]  # Limit to first 5
                file_paths = []
                for entity_id in entity_ids:
                    if entity_id in id_mapping:
                        file_paths.append(id_mapping[entity_id])
                    else:
                        file_paths.append(f"entity_{entity_id}")
            
            # Format files changed as ['filepath1','filepath2']
            files_changed_formatted = str(file_paths) if file_paths else "[]"
            
            # Map current verdict: 0=Pass, 1=Fail, 2=Error/Skip -> treat as Fail
            current_verdict = int(execution['verdict'])
            if current_verdict == 2:
                current_verdict = 1
            
            # Build the record
            record = {
                'Id': len(output_records) + 1,  # Sequential unique ID
                'Name': test_name_map.get(test_id, f"test_{test_id}"),
                'Duration': execution['duration'],
                'CalcPrio': 0,  # Fixed to 0 as requested
                'LastRun': last_run,
                'LastResults': f"[{','.join(last_results)}]" if last_results else "[]",
                'Verdict': current_verdict,  # Use mapped verdict (0 or 1)
                'Cycle': build_to_cycle.get(build_id, 0),
                'CommitMsg': build_info.get(build_id, {}).get('commit_messages', f'Build {build_id}'),
                'FilesChanged': files_changed_formatted,
                'BuildStartedAt': build_data.get('started_at', ''),
                'LocAdded': build_data.get('loc_added', 0),
                'LocDeleted': build_data.get('loc_deleted', 0)
            }
            
            output_records.append(record)
        
        # Create DataFrame
        result_df = pd.DataFrame(output_records)
        
        # Save to file if specified
        if output_file:
            result_df.to_csv(output_file, index=False)
            print(f"✓ Dataset saved to: {output_file}")
        
        print(f"✓ Generated enhanced dataset with {len(result_df)} test execution records")
        return result_df


def main():
    parser = argparse.ArgumentParser(description='Generate enhanced TCP datasets from CI/CD data')
    parser.add_argument('--project', type=str, help='Specific project to process')
    parser.add_argument('--list', action='store_true', help='List available projects')
    parser.add_argument('--output-dir', type=str, default='tcp_datasets_enhanced', 
                       help='Output directory for generated datasets')
    parser.add_argument('--base-path', type=str, default='.', 
                       help='Base path to TCP-CI_Dataset directory')
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = EnhancedTCPDatasetGenerator(args.base_path)
    
    # List projects if requested
    if args.list:
        projects = generator.get_available_projects()
        print("Available projects:")
        for i, project in enumerate(projects, 1):
            print(f"{i:2d}. {project}")
        return
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    if args.project:
        # Process specific project
        projects = [args.project]
    else:
        # Process all projects
        projects = generator.get_available_projects()
        print(f"Found {len(projects)} projects to process")
    
    # Generate datasets
    for project in projects:
        try:
            output_file = output_dir / f"{project}_enhanced_tcp_dataset.csv"
            dataset = generator.generate_dataset(project, output_file)
            print(f"✓ Completed {project}: {len(dataset)} records")
        except Exception as e:
            print(f"✗ Error processing {project}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✓ All enhanced datasets saved to: {output_dir}")


if __name__ == "__main__":
    main()