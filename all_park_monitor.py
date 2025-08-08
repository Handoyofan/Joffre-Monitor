#!/usr/bin/env python3
"""
Joffre Lakes Monitor - Check Today, Tomorrow, and Day After Tomorrow
"""

import requests
import json
import logging
from datetime import datetime, timedelta
import pytz
import os
from bs4 import BeautifulSoup
import time
from urllib.parse import urlencode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JoffreThreeDaysMonitor:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.base_url = "https://reserve.bcparks.ca"
        self.timezone = pytz.timezone('America/Vancouver')

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("Missing Telegram credentials")
        
        # Test telegram connection on startup
        self.test_telegram_connection()
    
    def get_target_dates(self):
        """Get today, tomorrow, and day after tomorrow"""
        now = datetime.now(self.timezone)
        dates = {
            'today': now,
            'tomorrow': now + timedelta(days=1),
            'day_after': now + timedelta(days=2)
        }
        return dates
    
    def format_date_for_url(self, date_obj):
        """Format date for different URL parameter formats"""
        return {
            'iso_date': date_obj.strftime('%Y-%m-%d'),
            'url_date': date_obj.strftime('%Y-%m-%d'),
            'display_date': date_obj.strftime('%B %d, %Y'),
            'short_date': date_obj.strftime('%m/%d/%Y'),
            'day_name': date_obj.strftime('%A')
        }
    
    def test_telegram_connection(self):
        """Test if Telegram bot is working"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()
                logger.info(f"✅ Telegram bot connected: {bot_info['result']['username']}")
                
                target_dates = self.get_target_dates()
                
                test_message = f"🤖 <b>Joffre Lakes Monitor Started</b>\n\n"
                test_message += f"📅 <b>Checking 3 Days:</b>\n"
                test_message += f"   🔹 Today: {self.format_date_for_url(target_dates['today'])['display_date']} ({target_dates['today'].strftime('%A')})\n"
                test_message += f"   🔹 Tomorrow: {self.format_date_for_url(target_dates['tomorrow'])['display_date']} ({target_dates['tomorrow'].strftime('%A')})\n"
                test_message += f"   🔹 Day After: {self.format_date_for_url(target_dates['day_after'])['display_date']} ({target_dates['day_after'].strftime('%A')})\n\n"
                test_message += f"🔍 <b>Status:</b> Bot is online and monitoring!"
                
                self.send_telegram(test_message)
            else:
                logger.error(f"❌ Telegram bot test failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Telegram connection test error: {e}")
    
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
                logger.info("✅ Telegram notification sent successfully")
                return True
            else:
                logger.error(f"❌ Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def build_joffre_urls(self, target_date, day_label):
        """Build URLs with date parameters for Joffre Lakes"""
        date_info = self.format_date_for_url(target_date)
        
        urls = [
            # Main facility page
            f"{self.base_url}/facility/joffre-lakes-provincial-park",
            
            # Day use registration with date parameter
            f"{self.base_url}/dayuse/registration?facility=joffre-lakes-provincial-park&date={date_info['iso_date']}",
            
            # Alternative date formats
            f"{self.base_url}/dayuse/registration?facility=joffre-lakes-provincial-park&arrivalDate={date_info['iso_date']}",
            
            # General day use page with date
            f"{self.base_url}/dayuse/registration?date={date_info['iso_date']}",
            
            # Search with facility and date
            f"{self.base_url}/search?facility=joffre-lakes-provincial-park&date={date_info['iso_date']}&partySize=1",
            
            # Booking page variations
            f"{self.base_url}/booking/joffre-lakes-provincial-park?date={date_info['iso_date']}",
            f"{self.base_url}/facility/joffre-lakes?date={date_info['iso_date']}"
        ]
        
        return urls
    
    def check_single_date_availability(self, target_date, day_label):
        """Check availability for a single date"""
        date_info = self.format_date_for_url(target_date)
        
        logger.info(f"\n📅 Checking {day_label.upper()}: {date_info['display_date']} ({date_info['day_name']})")
        logger.info("-" * 70)
        
        urls_to_check = self.build_joffre_urls(target_date, day_label)
        availability_found = False
        
        for i, url in enumerate(urls_to_check, 1):
            try:
                logger.info(f"🔍 [{i}/{len(urls_to_check)}] {url}")
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    logger.info(f"✅ Loaded ({len(response.text)} chars)")
                    
                    # Save debug content
                    self.save_debug_content(response.text, f"{day_label}_check_{i}", url, target_date, day_label)
                    
                    if self.parse_for_joffre_availability(response.text, url, target_date, day_label):
                        availability_found = True
                        break
                else:
                    logger.warning(f"⚠️ HTTP {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error: {e}")
                continue
            
            time.sleep(1)  # Be respectful
        
        result_emoji = "✅" if availability_found else "❌"
        logger.info(f"{result_emoji} {day_label.capitalize()} result: {'AVAILABLE' if availability_found else 'NOT AVAILABLE'}")
        
        return availability_found
    
    def check_all_dates_availability(self):
        """Check availability for all three dates"""
        try:
            target_dates = self.get_target_dates()
            results = {}
            
            # Check each date
            for day_key, date_obj in target_dates.items():
                day_labels = {
                    'today': 'today',
                    'tomorrow': 'tomorrow', 
                    'day_after': 'day after tomorrow'
                }
                
                day_label = day_labels[day_key]
                availability_found = self.check_single_date_availability(date_obj, day_label)
                
                results[day_key] = {
                    'date': date_obj,
                    'label': day_label,
                    'available': availability_found
                }
                
                # Small delay between date checks
                time.sleep(2)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Multi-date check failed: {e}")
            return {}
    
    def save_debug_content(self, html_content, filename_prefix, source_url, target_date, day_label):
        """Save debug content for analysis"""
        try:
            timestamp = int(time.time())
            date_str = target_date.strftime('%Y%m%d')
            
            # Save HTML
            html_filename = f"debug_{filename_prefix}_{date_str}_{timestamp}.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(f"<!-- Day Label: {day_label} -->\n")
                f.write(f"<!-- Target Date: {target_date.strftime('%Y-%m-%d %A')} -->\n")
                f.write(f"<!-- Source URL: {source_url} -->\n")
                f.write(f"<!-- Generated: {datetime.now()} -->\n\n")
                f.write(html_content)
            
            # Save text version
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text()
            
            text_filename = f"debug_{filename_prefix}_{date_str}_{timestamp}.txt"
            with open(text_filename, 'w', encoding='utf-8') as f:
                f.write(f"Day Label: {day_label}\n")
                f.write(f"Target Date: {target_date.strftime('%Y-%m-%d %A')}\n")
                f.write(f"Source URL: {source_url}\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write("=" * 80 + "\n\n")
                f.write(text_content)
            
            logger.debug(f"💾 Saved: {html_filename}, {text_filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save debug content: {e}")
    
    def parse_for_joffre_availability(self, html_content, source_url, target_date, day_label):
        try:
            now = datetime.now(self.timezone)
            soup = BeautifulSoup(html_content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Check for Joffre Lakes content
            joffre_keywords = ['joffre', 'joffrey']
            has_joffre_content = any(keyword in page_text for keyword in joffre_keywords)
            
            # Check for the specific date
            date_info = self.format_date_for_url(target_date)
            date_keywords = [
                date_info['iso_date'],
                target_date.strftime('%B %d').lower(),
                target_date.strftime('%b %d').lower(),
                target_date.strftime('%d %B').lower(),
                target_date.strftime('%m/%d'),
                target_date.strftime('%-d').lower()
            ]
            
            has_target_date = any(date_keyword in page_text for date_keyword in date_keywords)
            
            logger.debug(f"   Joffre content: {has_joffre_content}, Target date: {has_target_date}")
            
            if not has_joffre_content:
                return False
            
            # Enhanced availability indicators
            availability_indicators = [
                'available', 'book now', 'reserve now', 'select date', 
                'choose date', 'select time', 'purchase', 'add to cart',
                'book online', 'reservation available', 'make reservation',
                'day use pass', 'day pass available', 'passes available',
                'book this date', 'available for booking', 'reserve this date'
            ]
            
            unavailable_indicators = [
                'sold out', 'fully booked', 'no availability', 'unavailable',
                'no passes available', 'booking closed', 'not available',
                'waitlist only', 'no day use passes', 'passes sold out',
                'date unavailable', 'not accepting reservations', 'fully reserved'
            ]
            
            found_availability = [ind for ind in availability_indicators if ind in page_text]
            found_unavailable = [ind for ind in unavailable_indicators if ind in page_text]
            
            # Look for interactive elements
            booking_buttons = soup.find_all(['button', 'a'], string=lambda text: 
                text and any(word in text.lower() for word in ['book', 'reserve', 'purchase', 'select', 'available']))
            
            date_inputs = soup.find_all(['input', 'select'], attrs={
                'name': lambda x: x and any(word in x.lower() for word in ['date', 'arrival', 'visit'])
            })
            
            has_interactive_elements = len(booking_buttons) > 0 or len(date_inputs) > 0
            
            logger.debug(f"   Availability terms: {found_availability}")
            logger.debug(f"   Unavailable terms: {found_unavailable}")
            logger.debug(f"   Interactive elements: {has_interactive_elements}")
            
            # Decision logic
            has_availability_text = len(found_availability) > 0
            has_unavailable_text = len(found_unavailable) > 0
            
            if (has_availability_text or has_interactive_elements) and not has_unavailable_text:
                logger.info(f"🎉 AVAILABILITY DETECTED FOR {day_label.upper()}!")
                
                message = f"🏔️ <b>JOFFRE LAKES AVAILABLE!</b> 🎉\n\n"
                message += f"📅 <b>DATE:</b> {date_info['display_date']}\n"
                message += f"🗓️ <b>Day:</b> {date_info['day_name']}\n"
                message += f"⏰ <b>When:</b> {day_label.title()}\n\n"
                message += f"🎫 <b>Status:</b> Availability detected\n"
                message += f"🔗 <b>BOOK NOW:</b> {source_url}\n\n"
                
                if found_availability:
                    message += f"✅ <b>Indicators:</b> {', '.join(found_availability[:2])}\n"
                if has_interactive_elements:
                    message += f"🔘 <b>Booking:</b> Interactive elements found\n"
                
                message += f"\n⚡ <b>URGENT:</b> Joffre spots disappear in minutes!\n"
                message += f"🏃‍♂️ <b>Book immediately!</b>\n\n"
                message += f"🕐 <b>Found:</b> {now.strftime('%H:%M:%S')}"
                
                self.send_telegram(message)
                return True
            
            elif has_unavailable_text:
                logger.debug(f"❌ {day_label.capitalize()} unavailable")
                return False
            
            else:
                logger.debug(f"❓ {day_label.capitalize()} status unclear")
                return False
                
        except Exception as e:
            logger.error(f"❌ Parse error for {day_label}: {e}")
            return False
    
    def send_summary_notification(self, results):
        """Send a summary of all date checks"""
        now = datetime.now(self.timezone)
        current_hour = now.hour
        
        # Send summary during daytime hours
        if 6 <= current_hour <= 23:
            available_dates = [info for info in results.values() if info['available']]
            
            if available_dates:
                # At least one date available - already sent individual notifications
                return
            
            # No availability found - send summary
            message = f"📊 <b>Joffre Lakes Check Summary</b>\n\n"
            
            for day_key in ['today', 'tomorrow', 'day_after']:
                if day_key in results:
                    info = results[day_key]
                    date_str = self.format_date_for_url(info['date'])
                    status = "✅ AVAILABLE" if info['available'] else "❌ No availability"
                    message += f"🔹 <b>{info['label'].title()}:</b> {date_str['display_date']} ({date_str['day_name']}) - {status}\n"
            
            message += f"\n⏰ <b>Checked:</b> {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"🔄 <b>Next check:</b> Next scheduled run\n\n"
            message += f"📱 You'll get instant alerts when spots appear!"
            
            # Only send summary every few hours to avoid spam
            if current_hour in [7, 12, 19]:
                self.send_telegram(message)
    
    def run_comprehensive_check(self):
        start_time = datetime.now(self.timezone)
        logger.info("=" * 80)
        logger.info("🚀 JOFFRE LAKES 3-DAY COMPREHENSIVE CHECK")
        logger.info("=" * 80)
        
        try:
            results = self.check_all_dates_availability()
            
            if results:
                logger.info("\n📊 FINAL RESULTS:")
                logger.info("=" * 50)
                
                total_available = 0
                for day_key in ['today', 'tomorrow', 'day_after']:
                    if day_key in results:
                        info = results[day_key]
                        status = "✅ AVAILABLE" if info['available'] else "❌ NOT AVAILABLE"
                        logger.info(f"{status}: {info['label'].title()} - {self.format_date_for_url(info['date'])['display_date']}")
                        if info['available']:
                            total_available += 1
                
                logger.info(f"\n🎯 SUMMARY: {total_available}/3 dates have availability")
                
                # Send summary notification
                self.send_summary_notification(results)
            
            else:
                logger.error("❌ No results obtained from date checks")
            
            duration = (datetime.now(self.timezone) - start_time).total_seconds()
            logger.info(f"\n⏱️ Total check time: {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"❌ Comprehensive check failed: {e}")
            
            now = datetime.now(self.timezone)
            if 6 <= now.hour <= 23:
                error_message = f"⚠️ <b>Monitor Error</b>\n\n"
                error_message += f"❌ Failed during 3-day availability check\n"
                error_message += f"🐛 Error: {str(e)[:150]}\n"
                error_message += f"⏰ Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                error_message += f"🔄 Will retry on next scheduled run"
                
                self.send_telegram(error_message)
        
        logger.info("=" * 80)
        logger.info("✅ 3-DAY CHECK COMPLETED")
        logger.info("=" * 80)

def main():
    try:
        logger.info("🚀 Starting Joffre Lakes 3-Day Monitor...")
        checker = JoffreThreeDaysMonitor()
        checker.run_comprehensive_check()
        
    except Exception as e:
        error_msg = f"💥 Fatal error: {e}"
        print(error_msg)
        logger.error(error_msg)

if __name__ == "__main__":
    main()
