#!/usr/bin/env python3
"""
Joffre Lakes Single Check - Cloud Optimized Version
"""

import requests
import json
import logging
from datetime import datetime
import os
from bs4 import BeautifulSoup
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JoffreSingleCheck:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = "https://reserve.bcparks.ca"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("Missing Telegram credentials")
    
    def send_telegram(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def check_joffre_availability(self):
        try:
            urls_to_check = [
                f"{self.base_url}/dayuse/registration",
                f"{self.base_url}/facility/joffre-lakes-provincial-park",
                f"{self.base_url}/dayuse/registration?facility=joffre-lakes"
            ]
            
            availability_found = False
            
            for url in urls_to_check:
                try:
                    logger.info(f"Checking URL: {url}")
                    response = self.session.get(url, timeout=15)
                    
                    if response.status_code == 200:
                        if self.parse_for_joffre_availability(response.text, url):
                            availability_found = True
                            break
                            
                except Exception as e:
                    logger.debug(f"Error checking {url}: {e}")
                    continue
                
                time.sleep(0.5)
            
            return availability_found
            
        except Exception as e:
            logger.error(f"Availability check failed: {e}")
            return False
    
    def parse_for_joffre_availability(self, html_content, source_url):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Check if this page mentions Joffre Lakes
            joffre_keywords = ['joffre', 'joffrey']
            has_joffre_content = any(keyword in page_text for keyword in joffre_keywords)
            
            if not has_joffre_content:
                logger.debug(f"No Joffre content found on {source_url}")
                return False
            
            logger.info("Found Joffre Lakes content, checking availability...")
            
            availability_indicators = ['available', 'book now', 'reserve now', 'select date']
            unavailable_indicators = ['sold out', 'fully booked', 'no availability', 'unavailable']
            
            has_availability = any(indicator in page_text for indicator in availability_indicators)
            is_unavailable = any(indicator in page_text for indicator in unavailable_indicators)
            
            if has_availability and not is_unavailable:
                logger.info("Potential availability detected!")
                
                message = f"🏔️ <b>JOFFRE LAKES AVAILABILITY DETECTED!</b> 🎉\n\n"
                message += f"📍 <b>Location:</b> Joffre Lakes Provincial Park\n"
                message += f"🎫 <b>Status:</b> Availability indicators found\n"
                message += f"🔗 <b>CHECK NOW:</b> {source_url}\n"
                message += f"⏰ <b>Found:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                message += f"💨 <b>URGENT:</b> Joffre Lakes spots disappear within minutes!\n"
                message += f"🏃‍♂️ <b>Go book immediately!</b>"
                
                self.send_telegram(message)
                return True
            
            elif is_unavailable:
                logger.info("Joffre Lakes confirmed unavailable")
                return False
            
            else:
                logger.info("Joffre Lakes status unclear from page content")
                return False
                
        except Exception as e:
            logger.error(f"Error parsing content from {source_url}: {e}")
            return False
    
    def send_daily_summary(self):
        current_hour = datetime.now().hour
        
        if current_hour in [8, 20]:
            message = f"📊 <b>Joffre Lakes Daily Check</b>\n"
            message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            message += f"🔍 Monitoring active - checking every 10 minutes\n"
            message += f"🏔️ No availability found in recent checks\n"
            message += f"📱 You'll get instant alerts when spots open up"
            
            self.send_telegram(message)
    
    def run_single_check(self):
        start_time = datetime.now()
        logger.info("=== Starting Joffre Lakes availability check ===")
        
        try:
            availability_found = self.check_joffre_availability()
            
            if availability_found:
                logger.info("✅ Availability found and notification sent!")
            else:
                logger.info("❌ No availability found")
            
            self.send_daily_summary()
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Check completed in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Single check failed: {e}")
            
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 22:
                error_message = f"⚠️ <b>Monitor Error</b>\n\n"
                error_message += f"Failed to check Joffre Lakes availability\n"
                error_message += f"Error: {str(e)}\n"
                error_message += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                self.send_telegram(error_message)
        
        logger.info("=== Check completed ===")

def main():
    try:
        checker = JoffreSingleCheck()
        checker.run_single_check()
        
    except Exception as e:
        print(f"Fatal error: {e}")
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()