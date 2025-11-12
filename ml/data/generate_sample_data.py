"""
Generate synthetic sample data for testing the ML pipeline.

Creates dummy keypoint sequences for ASL, ISL, and BSL signs.
"""

import os
import json
import numpy as np
from pathlib import Path
import argparse


def generate_keypoint_sequence(
    num_frames: int = 30,
    num_keypoints: int = 543,
    variation: float = 0.1
) -> np.ndarray:
    """
    Generate synthetic keypoint sequence.
    
    Args:
        num_frames: Number of frames in sequence
        num_keypoints: Number of keypoints per frame
        variation: Amount of random variation
        
    Returns:
        Keypoint sequence of shape (num_frames, num_keypoints, 3)
    """
    # Generate base pose
    base_pose = np.random.randn(num_keypoints, 3) * 0.3
    
    # Generate temporal sequence with smooth transitions
    sequence = []
    for i in range(num_frames):
        # Add temporal variation
        t = i / num_frames
        noise = np.random.randn(num_keypoints, 3) * variation
        
        # Sinusoidal motion for more realistic movement
        motion = np.sin(2 * np.pi * t) * 0.1
        
        frame = base_pose + noise + motion
        sequence.append(frame)
    
    return np.array(sequence)


def create_sample_dataset(
    output_dir: str,
    signs_per_language: int = 10,
    samples_per_sign: int = 5,
    num_frames: int = 30
):
    """
    Create sample dataset with multiple sign languages.
    
    Args:
        output_dir: Output directory for dataset
        signs_per_language: Number of different signs per language
        samples_per_sign: Number of samples per sign
        num_frames: Number of frames per sample
    """
    output_path = Path(output_dir)
    
    # Define sign languages and sample signs
    languages = {
        "ASL": ["HELLO", "GOODBYE", "THANK_YOU", "PLEASE", "YES", 
                "NO", "SORRY", "HELP", "LOVE", "FRIEND"],
        "ISL": ["NAMASTE", "DHANYAVAAD", "KRIPAYA", "HAA", "NAHI",
                "MAAF_KIJIYE", "MADAD", "PYAAR", "DOST", "SHUBH"],
        "BSL": ["HELLO", "GOODBYE", "THANKS", "PLEASE", "YES",
                "NO", "SORRY", "HELP", "LOVE", "MATE"],
    }
    
    # Create train and validation splits
    for split in ["train", "val"]:
        split_dir = output_path / split
        split_dir.mkdir(parents=True, exist_ok=True)
        
        # Adjust sample count for validation (smaller)
        samples_count = samples_per_sign if split == "train" else max(1, samples_per_sign // 2)
        
        class_to_idx = {}
        class_idx = 0
        
        for language, signs in languages.items():
            print(f"\nGenerating {split} data for {language}...")
            
            for sign in signs[:signs_per_language]:
                # Create class directory
                class_name = f"{language}_{sign}"
                class_dir = split_dir / class_name
                class_dir.mkdir(exist_ok=True)
                
                class_to_idx[class_name] = class_idx
                class_idx += 1
                
                # Generate samples
                for sample_idx in range(samples_count):
                    # Generate keypoint sequence
                    keypoints = generate_keypoint_sequence(
                        num_frames=num_frames + np.random.randint(-5, 5),  # Variable length
                        variation=0.1 + np.random.rand() * 0.05  # Random variation
                    )
                    
                    # Save as numpy file
                    sample_path = class_dir / f"sample_{sample_idx:03d}.npy"
                    np.save(sample_path, keypoints)
                
                print(f"  Created {samples_count} samples for {class_name}")
        
        # Save class mapping
        labels_file = split_dir / "labels.json"
        with open(labels_file, 'w') as f:
            json.dump(class_to_idx, f, indent=2)
        
        print(f"\nSaved {split} labels to {labels_file}")
        print(f"Total classes: {len(class_to_idx)}")


def create_demo_video_samples(output_dir: str):
    """
    Create demo video file placeholders.
    
    Args:
        output_dir: Output directory
    """
    demo_dir = Path(output_dir) / "demo_videos"
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    # Create placeholder text files (actual videos would be too large)
    demo_signs = ["HELLO", "THANK_YOU", "GOODBYE"]
    
    for sign in demo_signs:
        placeholder = demo_dir / f"{sign}_demo.txt"
        with open(placeholder, 'w') as f:
            f.write(f"Placeholder for {sign} demo video\n")
            f.write(f"In production, this would be a video file showing the {sign} sign.\n")
            f.write(f"Format: MP4, Duration: 2-3 seconds\n")
    
    print(f"\nCreated demo video placeholders in {demo_dir}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Generate sample sign language dataset")
    parser.add_argument("--output", type=str, default="../sample_data", 
                       help="Output directory")
    parser.add_argument("--signs-per-language", type=int, default=10,
                       help="Number of signs per language")
    parser.add_argument("--samples-per-sign", type=int, default=5,
                       help="Number of samples per sign")
    parser.add_argument("--num-frames", type=int, default=30,
                       help="Number of frames per sample")
    args = parser.parse_args()
    
    print("=" * 60)
    print("SignLink AI - Sample Data Generator")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Output directory: {args.output}")
    print(f"  Signs per language: {args.signs_per_language}")
    print(f"  Samples per sign: {args.samples_per_sign}")
    print(f"  Frames per sample: {args.num_frames}")
    print(f"  Languages: ASL, ISL, BSL")
    
    # Create dataset
    create_sample_dataset(
        output_dir=args.output,
        signs_per_language=args.signs_per_language,
        samples_per_sign=args.samples_per_sign,
        num_frames=args.num_frames
    )
    
    # Create demo videos
    create_demo_video_samples(args.output)
    
    print("\n" + "=" * 60)
    print("Sample data generation complete!")
    print("=" * 60)
    print(f"\nDataset structure:")
    print(f"  {args.output}/train/  - Training data")
    print(f"  {args.output}/val/    - Validation data")
    print(f"  {args.output}/demo_videos/ - Demo placeholders")
    print(f"\nYou can now train a model using:")
    print(f"  python train.py --config configs/demo_config.yaml")


if __name__ == "__main__":
    main()
