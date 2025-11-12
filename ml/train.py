"""
Training script for sign language recognition model.

Supports distributed training, mixed precision, and experiment tracking.
"""

import os
import argparse
import yaml
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torch.cuda.amp import autocast, GradScaler
from tqdm import tqdm
from pathlib import Path
import json

from models.sign_language_model import create_model
from data.dataset import SignLanguageDataset
from training.trainer import Trainer
from training.evaluator import Evaluator


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Train sign language recognition model")
    parser.add_argument("--config", type=str, required=True, help="Path to config file")
    parser.add_argument("--epochs", type=int, default=None, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size")
    parser.add_argument("--lr", type=float, default=None, help="Learning rate")
    parser.add_argument("--device", type=str, default="cuda", help="Device (cuda/cpu)")
    parser.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
    parser.add_argument("--output-dir", type=str, default="models/checkpoints", help="Output directory")
    return parser.parse_args()


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def setup_training(config: dict, args):
    """
    Setup training components.
    
    Returns:
        Tuple of (model, train_loader, val_loader, optimizer, scheduler, criterion)
    """
    # Override config with command line args
    if args.epochs:
        config['training']['epochs'] = args.epochs
    if args.batch_size:
        config['training']['batch_size'] = args.batch_size
    if args.lr:
        config['training']['learning_rate'] = args.lr
    
    # Set device
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Create model
    model = create_model(
        model_type=config['model']['type'],
        num_classes=config['model']['num_classes'],
        hidden_dim=config['model'].get('hidden_dim', 256),
        num_lstm_layers=config['model'].get('num_lstm_layers', 2),
        dropout=config['model'].get('dropout', 0.3),
    )
    model = model.to(device)
    
    print(f"Model created with {sum(p.numel() for p in model.parameters()):,} parameters")
    
    # Create datasets
    train_dataset = SignLanguageDataset(
        data_dir=config['data']['train_dir'],
        sequence_length=config['data']['sequence_length'],
        augment=True,
    )
    
    val_dataset = SignLanguageDataset(
        data_dir=config['data']['val_dir'],
        sequence_length=config['data']['sequence_length'],
        augment=False,
    )
    
    print(f"Train dataset: {len(train_dataset)} samples")
    print(f"Val dataset: {len(val_dataset)} samples")
    
    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=True,
        num_workers=config['training'].get('num_workers', 4),
        pin_memory=True,
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=False,
        num_workers=config['training'].get('num_workers', 4),
        pin_memory=True,
    )
    
    # Create optimizer
    optimizer = optim.AdamW(
        model.parameters(),
        lr=config['training']['learning_rate'],
        weight_decay=config['training'].get('weight_decay', 0.01),
    )
    
    # Create learning rate scheduler
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config['training']['epochs'],
        eta_min=config['training'].get('min_lr', 1e-6),
    )
    
    # Create loss function
    criterion = nn.CrossEntropyLoss()
    
    # Resume from checkpoint if specified
    start_epoch = 0
    if args.resume:
        print(f"Resuming from checkpoint: {args.resume}")
        checkpoint = torch.load(args.resume, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        print(f"Resumed from epoch {start_epoch}")
    
    return model, train_loader, val_loader, optimizer, scheduler, criterion, device, start_epoch


def train_epoch(
    model: nn.Module,
    train_loader: DataLoader,
    optimizer: optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    scaler: GradScaler,
    use_amp: bool = True,
) -> dict:
    """
    Train for one epoch.
    
    Returns:
        Dictionary with training metrics
    """
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    
    pbar = tqdm(train_loader, desc="Training")
    
    for batch_idx, (data, targets, lengths) in enumerate(pbar):
        data = data.to(device)
        targets = targets.to(device)
        lengths = lengths.to(device)
        
        optimizer.zero_grad()
        
        # Mixed precision training
        if use_amp:
            with autocast():
                logits, _ = model(data, lengths)
                loss = criterion(logits, targets)
            
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            logits, _ = model(data, lengths)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()
        
        # Calculate accuracy
        _, predicted = logits.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()
        
        total_loss += loss.item()
        
        # Update progress bar
        pbar.set_postfix({
            'loss': f'{loss.item():.4f}',
            'acc': f'{100. * correct / total:.2f}%'
        })
    
    avg_loss = total_loss / len(train_loader)
    accuracy = 100. * correct / total
    
    return {
        'loss': avg_loss,
        'accuracy': accuracy,
    }


def validate(
    model: nn.Module,
    val_loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> dict:
    """
    Validate model.
    
    Returns:
        Dictionary with validation metrics
    """
    model.eval()
    total_loss = 0
    correct = 0
    total = 0
    
    with torch.no_grad():
        pbar = tqdm(val_loader, desc="Validation")
        
        for data, targets, lengths in pbar:
            data = data.to(device)
            targets = targets.to(device)
            lengths = lengths.to(device)
            
            logits, _ = model(data, lengths)
            loss = criterion(logits, targets)
            
            _, predicted = logits.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
            
            total_loss += loss.item()
            
            pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{100. * correct / total:.2f}%'
            })
    
    avg_loss = total_loss / len(val_loader)
    accuracy = 100. * correct / total
    
    return {
        'loss': avg_loss,
        'accuracy': accuracy,
    }


def save_checkpoint(
    model: nn.Module,
    optimizer: optim.Optimizer,
    scheduler,
    epoch: int,
    metrics: dict,
    output_dir: str,
    is_best: bool = False,
):
    """Save model checkpoint"""
    os.makedirs(output_dir, exist_ok=True)
    
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
        'metrics': metrics,
    }
    
    # Save regular checkpoint
    checkpoint_path = os.path.join(output_dir, f'checkpoint_epoch_{epoch}.pth')
    torch.save(checkpoint, checkpoint_path)
    print(f"Saved checkpoint: {checkpoint_path}")
    
    # Save best model
    if is_best:
        best_path = os.path.join(output_dir, 'best_model.pth')
        torch.save(checkpoint, best_path)
        print(f"Saved best model: {best_path}")


def main():
    """Main training function"""
    args = parse_args()
    
    # Load configuration
    config = load_config(args.config)
    print(f"Loaded config from {args.config}")
    print(json.dumps(config, indent=2))
    
    # Setup training
    model, train_loader, val_loader, optimizer, scheduler, criterion, device, start_epoch = setup_training(config, args)
    
    # Mixed precision scaler
    scaler = GradScaler()
    use_amp = config['training'].get('use_amp', True) and device.type == 'cuda'
    
    # Training loop
    best_val_acc = 0
    history = {
        'train_loss': [],
        'train_acc': [],
        'val_loss': [],
        'val_acc': [],
    }
    
    for epoch in range(start_epoch, config['training']['epochs']):
        print(f"\nEpoch {epoch + 1}/{config['training']['epochs']}")
        print("-" * 50)
        
        # Train
        train_metrics = train_epoch(
            model, train_loader, optimizer, criterion, device, scaler, use_amp
        )
        
        # Validate
        val_metrics = validate(model, val_loader, criterion, device)
        
        # Update learning rate
        scheduler.step()
        
        # Log metrics
        print(f"\nTrain Loss: {train_metrics['loss']:.4f}, Train Acc: {train_metrics['accuracy']:.2f}%")
        print(f"Val Loss: {val_metrics['loss']:.4f}, Val Acc: {val_metrics['accuracy']:.2f}%")
        print(f"Learning Rate: {optimizer.param_groups[0]['lr']:.6f}")
        
        # Save history
        history['train_loss'].append(train_metrics['loss'])
        history['train_acc'].append(train_metrics['accuracy'])
        history['val_loss'].append(val_metrics['loss'])
        history['val_acc'].append(val_metrics['accuracy'])
        
        # Save checkpoint
        is_best = val_metrics['accuracy'] > best_val_acc
        if is_best:
            best_val_acc = val_metrics['accuracy']
        
        if (epoch + 1) % config['training'].get('save_freq', 5) == 0 or is_best:
            save_checkpoint(
                model, optimizer, scheduler, epoch,
                {'train': train_metrics, 'val': val_metrics},
                args.output_dir, is_best
            )
    
    # Save training history
    history_path = os.path.join(args.output_dir, 'training_history.json')
    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"\nTraining completed! Best validation accuracy: {best_val_acc:.2f}%")
    print(f"Model saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
