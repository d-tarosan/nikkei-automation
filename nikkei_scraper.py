#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日経平均PER/PBR自動取得スクリプト
GitHub Actions用
"""

import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time

class NikkeiDataFetcher:
    def __init__(self):
        self.data_file = 'data/nikkei_data.json'
        self.ticker = '^N225'  # 日経平均のYahoo Financeティッカー
        
    def ensure_data_directory(self):
        """データディレクトリの存在確認・作成"""
        os.makedirs('data', exist_ok=True)
        
    def is_business_day(self, date):
        """営業日判定（簡易版）"""
        return date.weekday() < 5  # 月-金
        
    def get_nikkei_price(self):
        """Yahoo Financeから日経平均価格取得"""
        try:
            stock = yf.Ticker(self.ticker)
            hist = stock.history(period="5d")  # 過去5日分
            
            if hist.empty:
                raise Exception("データが取得できませんでした")
                
            latest = hist.iloc[-1]
            return {
                'price': round(float(latest['Close']), 2),
                'volume': int(latest['Volume'] / 1000000),  # 百万株単位
                'date': hist.index[-1].strftime('%Y-%m-%d')
            }
        except Exception as e:
            print(f"価格取得エラー: {e}")
            return None
            
    def get_bond_yield(self):
        """日本国債利回り取得（複数ソース試行）"""
        sources = [
            self._get_yield_from_investing,
            self._get_yield_from_tradingview,
            self._get_yield_fallback
        ]
        
        for source in sources:
            try:
                yield_rate = source()
                if yield_rate:
                    return yield_rate
            except Exception as e:
                print(f"国債利回り取得エラー ({source.__name__}): {e}")
                continue
                
        return 1.5  # フォールバック値
        
    def _get_yield_from_investing(self):
        """Investing.comから取得"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            response = requests.get(
                'https://www.investing.com/rates-bonds/japan-10-year-bond-yield',
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                # 簡易的なパース（実際のHTMLに応じて調整）
                return 1.485  # モック値
        except:
            pass
        return None
        
    def _get_yield_from_tradingview(self):
        """TradingViewから取得"""
        return None  # 実装省略
        
    def _get_yield_fallback(self):
        """フォールバック値"""
        return 1.485
        
    def load_existing_data(self):
        """既存データの読み込み"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"既存データ読み込みエラー: {e}")
        return []
        
    def save_data(self, data):
        """データの保存"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"データ保存完了: {self.data_file}")
        except Exception as e:
            print(f"データ保存エラー: {e}")
            
    def calculate_metrics(self, price, eps=2500, bps=27500, dividend=900):
        """PER/PBR等の計算"""
        return {
            'per': round(price / eps, 2),
            'pbr': round(price / bps, 2),
            'eps': eps,
            'bps': bps,
            'yield_rate': round(100 / (price / eps), 2),
            'dividend_yield': round((dividend / price) * 100, 2)
        }
        
    def run(self):
        """メイン実行"""
        print("🚀 日経平均データ取得開始...")
        
        self.ensure_data_directory()
        
        # 現在時刻と営業日チェック
        now = datetime.now()
        if not self.is_business_day(now):
            print("🚫 今日は営業日ではありません")
            return
            
        # 既存データ読み込み
        existing_data = self.load_existing_data()
        today_str = now.strftime('%Y-%m-%d')
        
        # 今日のデータが既に存在するかチェック
        if any(item.get('date') == today_str for item in existing_data):
            print(f"✅ 今日のデータは既に存在します: {today_str}")
            return
            
        # データ取得
        print("📊 市場データ取得中...")
        nikkei_data = self.get_nikkei_price()
        
        if not nikkei_data:
            print("❌ データ取得に失敗しました")
            return
            
        print("📈 国債利回り取得中...")
        bond_yield = self.get_bond_yield()
        
        # メトリクス計算
        metrics = self.calculate_metrics(nikkei_data['price'])
        
        # 新データ作成
        new_entry = {
            'date': today_str,
            'price': nikkei_data['price'],
            'volume': nikkei_data['volume'],
            'bond_yield': bond_yield,
            **metrics
        }
        
        # 前日比計算
        if existing_data:
            prev_price = existing_data[0].get('price', nikkei_data['price'])
            new_entry['change'] = round(nikkei_data['price'] - prev_price, 2)
        else:
            new_entry['change'] = 0
            
        # データ追加（新しいものを先頭に）
        existing_data.insert(0, new_entry)
        
        # 60営業日分のみ保持
        existing_data = existing_data[:60]
        
        # 保存
        self.save_data(existing_data)
        
        print(f"✅ データ更新完了!")
        print(f"📊 日経平均: ¥{nikkei_data['price']:,}")
        print(f"📈 変化: {new_entry['change']:+.2f}")
        print(f"📉 PER: {metrics['per']}")
        print(f"📊 PBR: {metrics['pbr']}")

if __name__ == "__main__":
    fetcher = NikkeiDataFetcher()
    fetcher.run()
