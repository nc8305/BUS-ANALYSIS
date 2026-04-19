#!/usr/bin/env python3
"""
DATA SAMPLER - Trích xuất sample data từ file lớn
===============================================

Tool để tạo sample data từ file CSV lớn cho testing
- Multiple sampling strategies 
- Preserve data structure và patterns
- Generate manageable test files
"""

import pandas as pd
import os
import sys
from datetime import datetime

def create_sample_data(input_file, sample_strategies):
    """
    Tạo các sample files với different strategies
    """
    
    print("🔬 DATA SAMPLER - CREATING TEST DATA")
    print("=" * 50)
    
    # 1. Kiểm tra file gốc
    if not os.path.exists(input_file):
        print(f"❌ File không tồn tại: {input_file}")
        return
        
    file_size = os.path.getsize(input_file) / (1024*1024)  # MB
    print(f"📁 Input file: {input_file}")
    print(f"📊 File size: {file_size:.2f} MB")
    
    # 2. Đọc metadata trước
    print(f"\n🔍 ANALYZING SOURCE DATA...")
    
    try:
        # Đọc first few rows để check structure
        df_head = pd.read_csv(input_file, nrows=10)
        print(f"✅ Columns: {list(df_head.columns)}")
        print(f"✅ Data types: {df_head.dtypes.to_dict()}")
        
        # Count total rows (estimate)
        print(f"\n📊 ESTIMATING TOTAL ROWS...")
        line_count = 0
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_count, line in enumerate(f, 1):
                if line_count % 1000000 == 0:  # Progress every 1M lines
                    print(f"   Processed: {line_count:,} lines...")
                if line_count > 10000000:  # Stop after 10M for estimation
                    break
                    
        print(f"📋 Estimated rows: {line_count:,}")
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    # 3. Tạo samples với different strategies
    print(f"\n🎯 CREATING SAMPLE FILES...")
    
    output_dir = "data/samples"
    os.makedirs(output_dir, exist_ok=True)
    
    for strategy_name, config in sample_strategies.items():
        
        print(f"\n📝 Strategy: {strategy_name}")
        print(f"   Size: {config['size']} records")
        print(f"   Method: {config['method']}")
        
        try:
            if config['method'] == 'head':
                # Lấy N dòng đầu
                df_sample = pd.read_csv(input_file, nrows=config['size'])
                
            elif config['method'] == 'random':
                # Random sampling (cần đọc toàn bộ file - chỉ dùng cho file nhỏ)
                if file_size > 500:  # > 500MB thì skip random
                    print(f"   ⚠️ File quá lớn cho random sampling, skip...")
                    continue
                df_full = pd.read_csv(input_file)
                df_sample = df_full.sample(n=config['size'], random_state=42)
                
            elif config['method'] == 'time_range':
                # Lấy theo time range cụ thể
                chunk_size = 10000
                df_sample = pd.DataFrame()
                
                for chunk in pd.read_csv(input_file, chunksize=chunk_size):
                    # Filter theo datetime range
                    if 'datetime' in chunk.columns:
                        chunk['datetime'] = pd.to_datetime(chunk['datetime'])
                        
                        # Lấy dữ liệu trong 1 giờ đầu
                        start_time = chunk['datetime'].min()
                        end_time = start_time + pd.Timedelta(hours=config.get('hours', 1))
                        
                        filtered = chunk[
                            (chunk['datetime'] >= start_time) & 
                            (chunk['datetime'] <= end_time)
                        ]
                        
                        df_sample = pd.concat([df_sample, filtered])
                        
                        if len(df_sample) >= config['size']:
                            df_sample = df_sample.head(config['size'])
                            break
                            
            elif config['method'] == 'vehicle_subset':
                # Lấy subset theo vehicle IDs
                chunk_size = 10000
                df_sample = pd.DataFrame()
                target_vehicles = set()
                
                for chunk in pd.read_csv(input_file, chunksize=chunk_size):
                    if 'vehicle' in chunk.columns:
                        # Lấy first N unique vehicles
                        unique_vehicles = chunk['vehicle'].unique()
                        target_vehicles.update(unique_vehicles[:config.get('vehicles', 10)])
                        
                        if len(target_vehicles) >= config.get('vehicles', 10):
                            target_vehicles = set(list(target_vehicles)[:config.get('vehicles', 10)])
                            break
                
                # Lấy data cho target vehicles
                for chunk in pd.read_csv(input_file, chunksize=chunk_size):
                    if 'vehicle' in chunk.columns:
                        filtered = chunk[chunk['vehicle'].isin(target_vehicles)]
                        df_sample = pd.concat([df_sample, filtered])
                        
                        if len(df_sample) >= config['size']:
                            df_sample = df_sample.head(config['size'])
                            break
            
            # Lưu sample file
            if not df_sample.empty:
                output_file = f"{output_dir}/sample_{strategy_name}.csv"
                df_sample.to_csv(output_file, index=False)
                
                sample_size = os.path.getsize(output_file) / (1024*1024)  # MB
                print(f"   ✅ Created: {output_file}")
                print(f"   📊 Records: {len(df_sample):,}")
                print(f"   💾 Size: {sample_size:.2f} MB")
                
                # Show sample info
                if 'datetime' in df_sample.columns:
                    df_sample['datetime'] = pd.to_datetime(df_sample['datetime'])
                    print(f"   ⏰ Time range: {df_sample['datetime'].min()} → {df_sample['datetime'].max()}")
                
                if 'vehicle' in df_sample.columns:
                    unique_vehicles = df_sample['vehicle'].nunique()
                    print(f"   🚌 Vehicles: {unique_vehicles}")
                    
            else:
                print(f"   ❌ No data extracted for {strategy_name}")
                
        except Exception as e:
            print(f"   ❌ Error creating {strategy_name}: {e}")
    
    print(f"\n🎉 SAMPLE CREATION COMPLETED!")
    print(f"📂 Output directory: {output_dir}")
    return output_dir

def main():
    """Main function"""
    
    # Input file
    input_file = "data/raw_2025-04-01.csv"
    
    # Sample strategies
    sample_strategies = {
        
        # 1. Quick test - 1000 records đầu
        "quick_test": {
            "size": 1000,
            "method": "head",
            "description": "1K records đầu tiên - để test nhanh"
        },
        
        # 2. Small dev - 10K records đầu  
        "small_dev": {
            "size": 10000,
            "method": "head", 
            "description": "10K records - phát triển và debug"
        },
        
        # 3. Time-based - 1 giờ đầu
        "first_hour": {
            "size": 50000,
            "method": "time_range",
            "hours": 1,
            "description": "Dữ liệu trong 1 giờ đầu"
        },
        
        # 4. Vehicle subset - 10 xe bus đầu tiên
        "vehicle_subset": {
            "size": 25000, 
            "method": "vehicle_subset",
            "vehicles": 10,
            "description": "Theo dõi 10 xe bus cụ thể"
        },
        
        # 5. Medium test - 100K records
        "medium_test": {
            "size": 100000,
            "method": "head",
            "description": "100K records - test performance"
        } 
    }
    
    # Tạo samples
    output_dir = create_sample_data(input_file, sample_strategies)
    
    if output_dir:
        print(f"\n🚀 NEXT STEPS:")
        print(f"1. Check sample files in: {output_dir}")
        print(f"2. Start với 'quick_test' (1K records)")
        print(f"3. Scale lên 'small_dev' (10K records)")
        print(f"4. Test với 'first_hour' hoặc 'vehicle_subset'")
        print(f"5. Performance test với 'medium_test' (100K)")

if __name__ == "__main__":
    main()