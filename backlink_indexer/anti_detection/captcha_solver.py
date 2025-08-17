"""
CAPTCHA solving integration for anti-detection
Supports 2Captcha, hCaptcha, and other popular services
"""

import time
import json
import logging
import requests
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from ..models import CaptchaChallenge


class CaptchaSolver(ABC):
    """Abstract base class for CAPTCHA solving services"""
    
    @abstractmethod
    def solve_recaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve reCAPTCHA challenge"""
        pass
    
    @abstractmethod
    def solve_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve hCAPTCHA challenge"""
        pass
    
    @abstractmethod
    def solve_text_captcha(self, image_data: bytes) -> Optional[str]:
        """Solve text-based CAPTCHA"""
        pass


class TwoCaptchaSolver(CaptchaSolver):
    """2Captcha service integration"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://2captcha.com"
        self.logger = logging.getLogger(__name__)
    
    def solve_recaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve reCAPTCHA v2/v3 using 2Captcha"""
        try:
            # Submit CAPTCHA
            submit_data = {
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': site_key,
                'pageurl': page_url,
                'json': 1
            }
            
            submit_response = requests.post(
                f"{self.base_url}/in.php",
                data=submit_data,
                timeout=30
            )
            
            submit_result = submit_response.json()
            
            if submit_result.get('status') != 1:
                self.logger.error(f"Failed to submit reCAPTCHA: {submit_result.get('error_text')}")
                return None
            
            captcha_id = submit_result.get('request')
            
            # Poll for solution
            for attempt in range(30):  # 5-minute timeout
                time.sleep(10)
                
                result_response = requests.get(
                    f"{self.base_url}/res.php?key={self.api_key}&action=get&id={captcha_id}&json=1",
                    timeout=30
                )
                
                result_data = result_response.json()
                
                if result_data.get('status') == 1:
                    return result_data.get('request')
                elif result_data.get('error_text') == 'CAPCHA_NOT_READY':
                    continue
                else:
                    self.logger.error(f"CAPTCHA solving failed: {result_data.get('error_text')}")
                    return None
            
            self.logger.error("CAPTCHA solving timeout")
            return None
            
        except Exception as e:
            self.logger.error(f"Error solving reCAPTCHA: {str(e)}")
            return None
    
    def solve_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Solve hCAPTCHA using 2Captcha"""
        try:
            # Submit CAPTCHA
            submit_data = {
                'key': self.api_key,
                'method': 'hcaptcha',
                'sitekey': site_key,
                'pageurl': page_url,
                'json': 1
            }
            
            submit_response = requests.post(
                f"{self.base_url}/in.php",
                data=submit_data,
                timeout=30
            )
            
            submit_result = submit_response.json()
            
            if submit_result.get('status') != 1:
                self.logger.error(f"Failed to submit hCAPTCHA: {submit_result.get('error_text')}")
                return None
            
            captcha_id = submit_result.get('request')
            
            # Poll for solution
            for attempt in range(30):
                time.sleep(10)
                
                result_response = requests.get(
                    f"{self.base_url}/res.php?key={self.api_key}&action=get&id={captcha_id}&json=1",
                    timeout=30
                )
                
                result_data = result_response.json()
                
                if result_data.get('status') == 1:
                    return result_data.get('request')
                elif result_data.get('error_text') == 'CAPCHA_NOT_READY':
                    continue
                else:
                    self.logger.error(f"hCAPTCHA solving failed: {result_data.get('error_text')}")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error solving hCAPTCHA: {str(e)}")
            return None
    
    def solve_text_captcha(self, image_data: bytes) -> Optional[str]:
        """Solve text-based CAPTCHA using 2Captcha"""
        try:
            import base64
            
            # Submit CAPTCHA
            submit_data = {
                'key': self.api_key,
                'method': 'base64',
                'body': base64.b64encode(image_data).decode('utf-8'),
                'json': 1
            }
            
            submit_response = requests.post(
                f"{self.base_url}/in.php",
                data=submit_data,
                timeout=30
            )
            
            submit_result = submit_response.json()
            
            if submit_result.get('status') != 1:
                self.logger.error(f"Failed to submit text CAPTCHA: {submit_result.get('error_text')}")
                return None
            
            captcha_id = submit_result.get('request')
            
            # Poll for solution
            for attempt in range(20):
                time.sleep(5)
                
                result_response = requests.get(
                    f"{self.base_url}/res.php?key={self.api_key}&action=get&id={captcha_id}&json=1",
                    timeout=30
                )
                
                result_data = result_response.json()
                
                if result_data.get('status') == 1:
                    return result_data.get('request')
                elif result_data.get('error_text') == 'CAPCHA_NOT_READY':
                    continue
                else:
                    self.logger.error(f"Text CAPTCHA solving failed: {result_data.get('error_text')}")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error solving text CAPTCHA: {str(e)}")
            return None


class MockCaptchaSolver(CaptchaSolver):
    """Mock CAPTCHA solver for testing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def solve_recaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Mock reCAPTCHA solution"""
        self.logger.info(f"Mock solving reCAPTCHA for {page_url}")
        time.sleep(2)  # Simulate solving time
        return "03AGdBq25SxXT-pmSeBXjzScW-EiocHwwpwqJRCAC3Q1QzkiVaOCb2o"
    
    def solve_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Mock hCAPTCHA solution"""
        self.logger.info(f"Mock solving hCAPTCHA for {page_url}")
        time.sleep(2)  # Simulate solving time
        return "P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.hadwYXNza2V5xQEO"
    
    def solve_text_captcha(self, image_data: bytes) -> Optional[str]:
        """Mock text CAPTCHA solution"""
        self.logger.info("Mock solving text CAPTCHA")
        time.sleep(1)  # Simulate solving time
        return "ABCD1234"


class CaptchaHandler:
    """High-level CAPTCHA handling interface"""
    
    def __init__(self, solver: CaptchaSolver):
        self.solver = solver
        self.logger = logging.getLogger(__name__)
        self.challenges = {}  # Store active challenges
    
    def create_challenge(self, challenge_type: str, site_key: str = None, 
                        page_url: str = None, image_data: bytes = None) -> CaptchaChallenge:
        """Create a new CAPTCHA challenge"""
        import uuid
        
        challenge_id = str(uuid.uuid4())
        
        challenge_data = {
            'site_key': site_key,
            'page_url': page_url,
        }
        
        if image_data:
            challenge_data['image_data'] = image_data
        
        challenge = CaptchaChallenge(
            challenge_id=challenge_id,
            challenge_type=challenge_type,
            site_key=site_key,
            challenge_data=challenge_data
        )
        
        self.challenges[challenge_id] = challenge
        return challenge
    
    def solve_challenge(self, challenge: CaptchaChallenge) -> bool:
        """Solve a CAPTCHA challenge"""
        try:
            solution = None
            
            if challenge.challenge_type == 'recaptcha':
                solution = self.solver.solve_recaptcha(
                    challenge.site_key,
                    challenge.challenge_data.get('page_url')
                )
            elif challenge.challenge_type == 'hcaptcha':
                solution = self.solver.solve_hcaptcha(
                    challenge.site_key,
                    challenge.challenge_data.get('page_url')
                )
            elif challenge.challenge_type == 'text':
                solution = self.solver.solve_text_captcha(
                    challenge.challenge_data.get('image_data')
                )
            
            if solution:
                challenge.solution = solution
                challenge.solved = True
                challenge.solved_at = time.time()
                
                self.logger.info(f"Successfully solved {challenge.challenge_type} CAPTCHA")
                return True
            else:
                self.logger.error(f"Failed to solve {challenge.challenge_type} CAPTCHA")
                return False
                
        except Exception as e:
            self.logger.error(f"Error solving CAPTCHA: {str(e)}")
            return False
    
    def get_solution(self, challenge_id: str) -> Optional[str]:
        """Get the solution for a challenge"""
        challenge = self.challenges.get(challenge_id)
        if challenge and challenge.solved:
            return challenge.solution
        return None
    
    def cleanup_old_challenges(self, max_age_seconds: int = 3600):
        """Remove old challenges to prevent memory leaks"""
        import time
        current_time = time.time()
        
        expired_challenges = []
        for challenge_id, challenge in self.challenges.items():
            age = current_time - challenge.created_at.timestamp()
            if age > max_age_seconds:
                expired_challenges.append(challenge_id)
        
        for challenge_id in expired_challenges:
            del self.challenges[challenge_id]
        
        if expired_challenges:
            self.logger.info(f"Cleaned up {len(expired_challenges)} expired CAPTCHA challenges")


def create_captcha_handler(api_key: Optional[str] = None, 
                          service: str = "2captcha") -> CaptchaHandler:
    """Factory function to create appropriate CAPTCHA handler"""
    
    if not api_key or service == "mock":
        return CaptchaHandler(MockCaptchaSolver())
    
    if service == "2captcha":
        return CaptchaHandler(TwoCaptchaSolver(api_key))
    
    # Add more services as needed
    # elif service == "anticaptcha":
    #     return CaptchaHandler(AntiCaptchaSolver(api_key))
    
    raise ValueError(f"Unsupported CAPTCHA service: {service}")