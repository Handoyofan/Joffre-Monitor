#!/usr/bin/env python3
"""
Multi-Park Monitor - Check Multiple BC Parks for 3 Days
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

class MultiParkMonitor:
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
        
        # Define parks to monitor
        self.parks = {
            'joffre': {
                'name': 'Joffre Lakes Provincial Park',
                'slug': 'joffre-lakes-provincial-park',
                'keywords': ['joffre', 'joffrey'],
                'priority': 1,  # 1 = highest priority
                'emoji': '🏔️'
            },
            'garibaldi': {
                'name': 'Garibaldi Provincial Park',
                'slug': 'garibaldi-provincial-park',
                'keywords': ['garibaldi'],
                'priority': 2,
                'emoji': '⛰️'
            },
            'golden-ears': {
                'name': 'Golden Ears Provincial Park',
                'slug': 'golden-ears-provincial-park',
                'keywords': ['golden ears', 'golden'],
                'priority': 3,
                'emoji': '🌲'
            },
            'alice-lake': {
                'name': 'Alice Lake Provincial Park',
                'slug': 'alice-lake-provincial-park',
                'keywords': ['alice lake', 'alice'],
                'priority': 4,
                'emoji': '🏞️'
            },
            'cultus-lake': {
                'name': 'Cultus Lake Provincial Park',
                'slug': 'cultus-lake-provincial-park',
                'keywords': ['cultus lake', 'cultus'],
                'priority': 5,
                'emoji': '🏊‍♀️'
            },
            'porteau-cove': {
                'name': 'Porteau Cove Provincial Park',
                'slug': 'porteau-cove-provincial-park',
                'keywords': ['porteau cove', 'porteau'],
                'priority': 6,
                'emoji': '🌊'
            }
        }
        
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
                
                test_message = f"🤖 <b>Multi-Park Monitor Started</b>\n\n"
                test_message += f"📅 <b>Checking 3 Days:</b>\n"
                test_message += f"   🔹 Today: {self.format_date_for_url(target_dates['today'])['display_date']} ({target_dates['today'].strftime('%A')})\n"
                test_message += f"   🔹 Tomorrow: {self.format_date_for_url(target_dates['tomorrow'])['display_date']} ({target_dates['tomorrow'].strftime('%A')})\n"
                test_message += f"   🔹 Day After: {self.format_date_for_url(target_dates['day_after'])['display_date']} ({target_dates['day_after'].strftime('%A')})\n\n"
                
                test_message += f"🏞️ <b>Monitoring {len(self.parks)} Parks:</b>\n"
                sorted_parks = sorted(self.parks.items(), key=lambda x: x[1]['priority'])
                for park_key, park_info in sorted_parks:
                    test_message += f"   {park_info['emoji']} {park_info['name']}\n"
                
                test_message += f"\n🔍 <b>Status:</b> Bot is online and monitoring!"
                
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
    
    def build_park_urls(self, park_info, target_date):
        """Build URLs for a specific park and date"""
        date_info = self.format_date_for_url(target_date)
        slug = park_info['slug']
        
        urls = [
            # Main facility page
            f"{self.base_url}/facility/{slug}",
            
            # Day use registration with date
            f"{self.base_url}/dayuse/registration?facility={slug}&date={date_info['iso_date']}",
            
            # Alternative date parameter
            f"{self.base_url}/dayuse/registration?facility={slug}&arrivalDate={date_info['iso_date']}",
            
            # General search
            f"{self.base_url}/search?facility={slug}&date={date_info['iso_date']}&partySize=1",
            
            # Booking variations
            f"{self.base_url}/booking/{slug}?date={date_info['iso_date']}"
        ]
        
        return urls
    
    def check_park_date_availability(self, park_key, park_info, target_date, day_label):
        """Check availability for a specific park and date"""
        date_info = self.format_date_for_url(target_date)
        
        logger.info(f"\n{park_info['emoji']} {park_info['name']} - {day_label.upper()}")
        logger.info(f"📅 {date_info['display_date']} ({date_info['day_name']})")
        logger.info("-" * 60)
        
        urls_to_check = self.build_park_urls(park_info, target_date)
        availability_found = False
        
        for i, url in enumerate(urls_to_check, 1):
            try:
                logger.info(f"🔍 [{i}/{len(urls_to_check)}] Checking...")
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    logger.info(f"✅ Loaded ({len(response.text)} chars)")
                    
                    # Save debug content
                    self.save_debug_content(response.text, f"{park_key}_{day_label}_{i}", url, target_date, park_key, day_label)
                    
                    if self.parse_for_park_availability(response.text, url, target_date, park_info, day_label):
                        availability_found = True
                        break
                else:
                    logger.warning(f"⚠️ HTTP {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error: {e}")
                continue
            
            time.sleep(0.8)  # Be respectful
        
        result_emoji = "✅" if availability_found else "❌"
        logger.info(f"{result_emoji} Result: {'AVAILABLE' if availability_found else 'NOT AVAILABLE'}")
        
        return availability_found
    
    def check_all_parks_and_dates(self):
        """Check all parks for all dates"""
        try:
            target_dates = self.get_target_dates()
            results = {}
            
            # Sort parks by priority (Joffre first)
            sorted_parks = sorted(self.parks.items(), key=lambda x: x[1]['priority'])
            
            for park_key, park_info in sorted_parks:
                logger.info(f"\n{'='*80}")
                logger.info(f"🏞️ CHECKING: {park_info['name'].upper()}")
                logger.info(f"{'='*80}")
                
                park_results = {}
                
                for day_key, date_obj in target_dates.items():
                    day_labels = {
                        'today': 'today',
                        'tomorrow': 'tomorrow', 
                        'day_after': 'day after tomorrow'
                    }
                    
                    day_label = day_labels[day_key]
                    availability_found = self.check_park_date_availability(park_key, park_info, date_obj, day_label)
                    
                    park_results[day_key] = {
                        'date': date_obj,
                        'label': day_label,
                        'available': availability_found
                    }
                    
                    # Brief pause between dates
                    time.sleep(1)
                
                results[park_key] = {
                    'park_info': park_info,
                    'dates': park_results
                }
                
                # Longer pause between parks
                time.sleep(2)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Multi-park check failed: {e}")
            return {}
    
    def save_debug_content(self, html_content, filename_prefix, source_url, target_date, park_key, day_label):
        """Save debug content for analysis"""
        try:
            timestamp = int(time.time())
            date_str = target_date.strftime('%Y%m%d')
            
            # Save HTML
            html_filename = f"debug_{filename_prefix}_{date_str}_{timestamp}.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(f"<!-- Park: {park_key} -->\n")
                f.write(f"<!-- Day Label: {day_label} -->\n")
                f.write(f"<!-- Target Date: {target_date.strftime('%Y-%m-%d %A')} -->\n")
                f.write(f"<!-- Source URL: {source_url} -->\n")
                f.write(f"<!-- Generated: {datetime.now()} -->\n\n")
                f.write(html_content)
            
            logger.debug(f"💾 Saved: {html_filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save debug content: {e}")
    
    def parse_for_park_availability(self, html_content, source_url, target_date, park_info, day_label):
        try:
            now = datetime.now(self.timezone)
            soup = BeautifulSoup(html_content, 'html.parser')
            page_text = soup.get_text().lower()
            
            # Check for park content
            has_park_content = any(keyword in page_text for keyword in park_info['keywords'])
            
            # Check for the specific date
            date_info = self.format_date_for_url(target_date)
            date_keywords = [
                date_info['iso_date'],
                target_date.strftime('%B %d').lower(),
                target_date.strftime('%b %d').lower(),
                target_date.strftime('%m/%d')
            ]
            
            has_target_date = any(date_keyword in page_text for date_keyword in date_keywords)
            
            logger.debug(f"   Park content: {has_park_content}, Target date: {has_target_date}")
            
            if not has_park_content:
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
            
            logger.debug(f"   Availability: {found_availability}")
            logger.debug(f"   Unavailable: {found_unavailable}")
            logger.debug(f"   Interactive: {has_interactive_elements}")
            
            # Decision logic
            has_availability_text = len(found_availability) > 0
            has_unavailable_text = len(found_unavailable) > 0
            
            if (has_availability_text or has_interactive_elements) and not has_unavailable_text:
                logger.info(f"🎉 AVAILABILITY DETECTED!")
                
                # Determine urgency level based on park priority
                if park_info['priority'] == 1:  # Joffre Lakes
                    urgency = "⚡ URGENT: This is Joffre Lakes - spots disappear in minutes!"
                    action = "🏃‍♂️ Book immediately!"
                elif park_info['priority'] <= 3:  # High priority parks
                    urgency = "🔥 High Priority: Popular park - book soon!"
                    action = "🚀 Reserve now!"
                else:
                    urgency = "📍 Good option available!"
                    action = "✅ Consider booking!"
                
                message = f"{park_info['emoji']} <b>{park_info['name'].upper()}</b> 🎉\n\n"
                message += f"📅 <b>DATE:</b> {date_info['display_date']}\n"
                message += f"🗓️ <b>Day:</b> {date_info['day_name']}\n"
                message += f"⏰ <b>When:</b> {day_label.title()}\n\n"
                message += f"🎫 <b>Status:</b> Availability detected\n"
                message += f"🔗 <b>BOOK:</b> {source_url}\n\n"
                
                if found_availability:
                    message += f"✅ <b>Indicators:</b> {', '.join(found_availability[:2])}\n"
                
                message += f"\n{urgency}\n{action}\n\n"
                message += f"🕐 <b>Found:</b> {now.strftime('%H:%M:%S')}"
                
                self.send_telegram(message)
                return True
            
            elif has_unavailable_text:
                logger.debug(f"❌ Unavailable")
                return False
            
            else:
                logger.debug(f"❓ Status unclear")
                return False
                
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            return False
    
    def send_comprehensive_summary(self, results):
        """Send a comprehensive summary of all parks and dates"""
        now = datetime.now(self.timezone)
        current_hour = now.hour
        
        # Send summary during reasonable hours
        if not (6 <= current_hour <= 23):
            return
        
        available_spots = []
        unavailable_parks = []
        
        # Collect results
        for park_key, park_data in results.items():
            park_info = park_data['park_info']
            dates = park_data['dates']
            
            park_available_dates = []
            for day_key in ['today', 'tomorrow', 'day_after']:
                if day_key in dates and dates[day_key]['available']:
                    park_available_dates.append(dates[day_key]['label'])
            
            if park_available_dates:
                available_spots.append({
                    'park': park_info,
                    'dates': park_available_dates
                })
            else:
                unavailable_parks.append(park_info)
        
        # If we found availability, individual notifications were already sent
        if available_spots:
            return
        
        # Send summary only if no availability found and during summary hours
        if current_hour not in [7, 14, 21]:
            return
        
        message = f"📊 <b>Multi-Park Monitor Summary</b>\n\n"
        message += f"⏰ <b>Check Time:</b> {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"🔍 <b>Parks Checked:</b> {len(self.parks)}\n"
        message += f"📅 <b>Days Checked:</b> 3 (Today, Tomorrow, Day After)\n\n"
        
        message += f"❌ <b>No Availability Found:</b>\n"
        sorted_parks = sorted(unavailable_parks, key=lambda x: x['priority'])
        for park_info in sorted_parks:
            message += f"   {park_info['emoji']} {park_info['name']}\n"
        
        message += f"\n🔄 <b>Next Check:</b> Next scheduled run\n"
        message += f"📱 You'll get instant alerts when spots appear!\n\n"
        message += f"💡 <i>Monitoring continues automatically</i>"
        
        self.send_telegram(message)
    
    def run_comprehensive_check(self):
        start_time = datetime.now(self.timezone)
        logger.info("=" * 100)
        logger.info("🚀 MULTI-PARK COMPREHENSIVE MONITOR - 3 DAY CHECK")
        logger.info("=" * 100)
        
        try:
            results = self.check_all_parks_and_dates()
            
            if results:
                logger.info(f"\n📊 FINAL RESULTS SUMMARY:")
                logger.info("=" * 80)
                
                total_available = 0
                total_checked = 0
                
                for park_key, park_data in results.items():
                    park_info = park_data['park_info']
                    dates = park_data['dates']
                    
                    available_dates = []
                    for day_key in ['today', 'tomorrow', 'day_after']:
                        total_checked += 1
                        if day_key in dates and dates[day_key]['available']:
                            available_dates.append(dates[day_key]['label'])
                            total_available += 1
                    
                    if available_dates:
                        logger.info(f"✅ {park_info['emoji']} {park_info['name']}: {', '.join(available_dates)}")
                    else:
                        logger.info(f"❌ {park_info['emoji']} {park_info['name']}: No availability")
                
                logger.info(f"\n🎯 OVERALL SUMMARY:")
                logger.info(f"   Available slots: {total_available}/{total_checked}")
                logger.info(f"   Parks with availability: {sum(1 for pd in results.values() if any(d['available'] for d in pd['dates'].values()))}/{len(results)}")
                
                # Send summary notification
                self.send_comprehensive_summary(results)
            
            else:
                logger.error("❌ No results obtained from checks")
            
            duration = (datetime.now(self.timezone) - start_time).total_seconds()
            logger.info(f"\n⏱️ Total runtime: {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"❌ Comprehensive check failed: {e}")
            
            now = datetime.now(self.timezone)
            if 6 <= now.hour <= 23:
                error_message = f"⚠️ <b>Multi-Park Monitor Error</b>\n\n"
                error_message += f"❌ Failed during comprehensive check\n"
                error_message += f"🐛 Error: {str(e)[:150]}\n"
                error_message += f"⏰ Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                error_message += f"🔄 Will retry on next scheduled run"
                
                self.send_telegram(error_message)
        
        logger.info("=" * 100)
        logger.info("✅ MULTI-PARK CHECK COMPLETED")
        logger.info("=" * 100)

def main():
    try:
        logger.info("🚀 Starting Multi-Park Monitor...")
        monitor = MultiParkMonitor()
        monitor.run_comprehensive_check()
        
    except Exception as e:
        error_msg = f"💥 Fatal error: {e}"
        print(error_msg)
        logger.error(error_msg)

if __name__ == "__main__":
    main()
