import time
import logging
import traceback
from web_driver import WebDriverManager
from ai_client import AIClient
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestAgent")

class TestAgent:
    def __init__(self):
        self.driver = None

    def run_autonomous_test(self, goal: str, provider: str = None, model: str = None, ui_callback=None, api_key: str = None) -> dict:
        """
        Runs an autonomous test where the AI decides actions in a loop to achieve a goal.
        ui_callback: Function(step_num, screenshot, thought, reason, action, status) to push updates to UI
        """
        provider = provider or Config.DEFAULT_PROVIDER
        model = model or Config.DEFAULT_MODEL
        self.driver = WebDriverManager()
        
        history = []
        steps_executed = []
        max_steps = 12
        step_count = 0
        success = False
        final_message = ""

        try:
            # 1. Start browser and navigate to target
            self.driver.navigate(Config.TARGET_URL)
            
            while step_count < max_steps:
                step_count += 1
                logger.info(f"--- Autonomous Step {step_count} ---")
                
                # Extract state
                dom_structure = self.driver.get_dom_structure()
                screenshot = self.driver.get_screenshot()
                
                # Ask AI what to do next
                ai_response = AIClient.analyze_page_state(
                    dom_structure=dom_structure,
                    screenshot_bytes=screenshot,
                    goal=goal,
                    history=history,
                    provider=provider,
                    model=model,
                    api_key=api_key
                )
                
                thought = ai_response.get("thought", "No thought provided.")
                action = ai_response.get("action", "fail").lower()
                selector = ai_response.get("selector", "")
                value = ai_response.get("value", "")
                reason = ai_response.get("reason", "Menjalankan tindakan otomatis.")
                
                logger.info(f"AI Thought: {thought}")
                logger.info(f"AI Decision: {action} on '{selector}' with value '{value}'")
                
                # Append to history for AI context (keep it simple)
                history.append({
                    "step": step_count,
                    "thought": thought,
                    "action": action,
                    "selector": selector,
                    "value": value
                })
                
                # Record details of this step for reporting
                step_detail = {
                    "step": step_count,
                    "thought": thought,
                    "action": action,
                    "selector": selector,
                    "value": value,
                    "reason": reason,
                    "status": "pending",
                    "screenshot": screenshot
                }
                steps_executed.append(step_detail)

                # Send initial update to Streamlit callback
                if ui_callback:
                    ui_callback(step_detail)
                
                # Execute action
                try:
                    if action == "click":
                        self.driver.safe_click(selector)
                        step_detail["status"] = "success"
                    elif action == "type":
                        self.driver.safe_type(selector, value)
                        step_detail["status"] = "success"
                    elif action == "select":
                        self.driver.safe_select(selector, value)
                        step_detail["status"] = "success"
                    elif action == "navigate":
                        self.driver.navigate(value)
                        step_detail["status"] = "success"
                    elif action == "verify":
                        verified = self.driver.safe_verify(value)
                        step_detail["status"] = "success" if verified else "failed"
                        if not verified:
                            raise AssertionError(f"Gagal memverifikasi adanya teks '{value}' di halaman.")
                    elif action == "finish":
                        success = True
                        step_detail["status"] = "success"
                        final_message = f"Pengujian Berhasil! AI menyatakan target tercapai: {reason}"
                        if ui_callback:
                            ui_callback(step_detail)
                        break
                    elif action == "fail":
                        success = False
                        step_detail["status"] = "failed"
                        final_message = f"Pengujian Gagal! AI menyatakan kegagalan: {reason}"
                        if ui_callback:
                            ui_callback(step_detail)
                        break
                    else:
                        raise ValueError(f"Aksi AI tidak dikenal: {action}")
                        
                except Exception as action_err:
                    logger.error(f"Error executing AI action: {action_err}")
                    step_detail["status"] = "failed"
                    step_detail["error"] = str(action_err)
                    
                    # We can try to self-heal or declare failure
                    success = False
                    final_message = f"Gagal mengeksekusi tindakan '{action}' pada selector '{selector}': {str(action_err)}"
                    if ui_callback:
                        ui_callback(step_detail)
                    break
                
                # Send updated status to Streamlit
                if ui_callback:
                    ui_callback(step_detail)
                    
                time.sleep(1.0) # Small pause for user observation
                
            if step_count >= max_steps and not success:
                final_message = "Pengujian dihentikan karena mencapai batas maksimal langkah (Max Steps)."
                
        except Exception as e:
            logger.error(f"Autonomous test run crashed: {e}")
            logger.error(traceback.format_exc())
            final_message = f"Sistem pengujian error: {str(e)}"
        finally:
            if self.driver:
                self.driver.close()
                
        return {
            "success": success,
            "steps": steps_executed,
            "message": final_message
        }

    def run_scenario_steps(self, steps: list, provider: str = None, model: str = None, ui_callback=None) -> dict:
        """
        Executes a predefined list of test steps sequentially.
        """
        self.driver = WebDriverManager()
        steps_executed = []
        success = True
        final_message = "Semua langkah skenario berhasil dieksekusi."

        try:
            self.driver.navigate(Config.TARGET_URL)
            
            for step_data in steps:
                step_num = step_data["step"]
                desc = step_data["description"]
                action = step_data["action"].lower()
                selector = step_data["selector"]
                value = step_data["value"]
                
                logger.info(f"Running Scenario Step {step_num}: {desc}")
                
                screenshot = self.driver.get_screenshot()
                step_detail = {
                    "step": step_num,
                    "thought": f"Mengeksekusi langkah terstruktur: {desc}",
                    "action": action,
                    "selector": selector,
                    "value": value,
                    "reason": desc,
                    "status": "pending",
                    "screenshot": screenshot
                }
                steps_executed.append(step_detail)
                
                if ui_callback:
                    ui_callback(step_detail)
                    
                try:
                    if action == "click":
                        self.driver.safe_click(selector)
                        step_detail["status"] = "success"
                    elif action == "type":
                        self.driver.safe_type(selector, value)
                        step_detail["status"] = "success"
                    elif action == "select":
                        self.driver.safe_select(selector, value)
                        step_detail["status"] = "success"
                    elif action == "navigate":
                        self.driver.navigate(value)
                        step_detail["status"] = "success"
                    elif action == "verify":
                        verified = self.driver.safe_verify(value)
                        step_detail["status"] = "success" if verified else "failed"
                        if not verified:
                            raise AssertionError(f"Gagal memverifikasi teks '{value}'")
                            
                except Exception as err:
                    step_detail["status"] = "failed"
                    step_detail["error"] = str(err)
                    success = False
                    final_message = f"Gagal pada langkah {step_num}: {desc}. Error: {str(err)}"
                    if ui_callback:
                        ui_callback(step_detail)
                    break
                    
                if ui_callback:
                    ui_callback(step_detail)
                time.sleep(0.8)

        except Exception as e:
            success = False
            final_message = f"Gagal menjalankan skenario: {str(e)}"
        finally:
            if self.driver:
                self.driver.close()
                
        return {
            "success": success,
            "steps": steps_executed,
            "message": final_message
        }

    def run_self_healing_test(self, steps: list, simulate_broken_idx: int = None, simulate_broken_selector: str = None, provider: str = None, model: str = None, ui_callback=None, api_key: str = None) -> dict:
        """
        Executes test steps, and if a selector fails, uses GenAI to dynamically heal the locator and continue.
        simulate_broken_idx: index of step to inject the broken selector (1-based index)
        """
        provider = provider or Config.DEFAULT_PROVIDER
        model = model or Config.DEFAULT_MODEL
        self.driver = WebDriverManager()
        
        steps_executed = []
        success = True
        final_message = "Semua langkah berhasil dieksekusi dengan self-healing."

        try:
            self.driver.navigate(Config.TARGET_URL)
            
            for idx, step_data in enumerate(steps):
                step_num = step_data["step"]
                desc = step_data["description"]
                action = step_data["action"].lower()
                selector = step_data["selector"]
                value = step_data["value"]
                
                # Simulate a broken selector if requested
                original_selector = selector
                is_simulated_broken = False
                if simulate_broken_idx is not None and step_num == simulate_broken_idx:
                    selector = simulate_broken_selector
                    is_simulated_broken = True
                    logger.info(f"Simulating broken selector on step {step_num}: changed '{original_selector}' to '{selector}'")

                logger.info(f"Running Step {step_num}: {desc}")
                
                screenshot = self.driver.get_screenshot()
                step_detail = {
                    "step": step_num,
                    "thought": f"Mengeksekusi langkah: {desc}" + (" (SIMULASI RUSAK)" if is_simulated_broken else ""),
                    "action": action,
                    "selector": selector,
                    "value": value,
                    "reason": desc,
                    "status": "pending",
                    "screenshot": screenshot,
                    "healed_log": ""
                }
                steps_executed.append(step_detail)
                
                if ui_callback:
                    ui_callback(step_detail)
                    
                try:
                    # Execute action
                    if action == "click":
                        # We use a short timeout of 5 seconds to speed up simulation of failure
                        self.driver.safe_click(selector, timeout=5000)
                        step_detail["status"] = "success"
                    elif action == "type":
                        self.driver.safe_type(selector, value, timeout=5000)
                        step_detail["status"] = "success"
                    elif action == "select":
                        self.driver.safe_select(selector, value, timeout=5000)
                        step_detail["status"] = "success"
                    elif action == "navigate":
                        self.driver.navigate(value)
                        step_detail["status"] = "success"
                    elif action == "verify":
                        verified = self.driver.safe_verify(value)
                        step_detail["status"] = "success" if verified else "failed"
                        if not verified:
                            raise AssertionError(f"Gagal memverifikasi teks '{value}'")
                            
                except Exception as err:
                    logger.warning(f"Step {step_num} failed with selector '{selector}'. Starting self-healing...")
                    step_detail["status"] = "healing"
                    step_detail["healed_log"] = f"Error: Elemen '{selector}' tidak ditemukan. Memanggil AI untuk pemulihan (Self-Healing)..."
                    if ui_callback:
                        ui_callback(step_detail)
                        
                    # 1. Get DOM Structure
                    dom_structure = self.driver.get_dom_structure()
                    
                    # 2. Ask AI to heal locator
                    healing_result = AIClient.heal_locator(
                        broken_locator=selector,
                        dom_structure=dom_structure,
                        error_message=str(err),
                        provider=provider,
                        model=model,
                        api_key=api_key
                    )
                    
                    healed = healing_result.get("healed", False)
                    new_selector = healing_result.get("new_selector", "")
                    confidence = healing_result.get("confidence", 0.0)
                    explanation = healing_result.get("explanation", "")
                    
                    if healed and new_selector:
                        heal_msg = f"Self-Healing Berhasil! AI menemukan selector pengganti: `{new_selector}` (Confidence: {confidence:.2f}). Alasan: {explanation}"
                        logger.info(heal_msg)
                        step_detail["healed_log"] = heal_msg
                        step_detail["selector"] = f"{new_selector} (Healed dari {selector})"
                        if ui_callback:
                            ui_callback(step_detail)
                            
                        # Try running with the healed selector
                        try:
                            time.sleep(1.0) # Small pause
                            if action == "click":
                                self.driver.safe_click(new_selector)
                            elif action == "type":
                                self.driver.safe_type(new_selector, value)
                            elif action == "select":
                                self.driver.safe_select(new_selector, value)
                            
                            step_detail["status"] = "success"
                            logger.info(f"Step {step_num} successfully completed using healed selector.")
                        except Exception as heal_err:
                            step_detail["status"] = "failed"
                            step_detail["healed_log"] += f"\n\n Gagal mengeksekusi selector hasil perbaikan: {str(heal_err)}"
                            success = False
                            final_message = f"Gagal mengeksekusi selector hasil perbaikan: {str(heal_err)}"
                            if ui_callback:
                                ui_callback(step_detail)
                            break
                    else:
                        heal_fail_msg = f"Self-Healing Gagal! AI tidak dapat menemukan selector pengganti yang cocok. Alasan: {explanation}"
                        logger.error(heal_fail_msg)
                        step_detail["status"] = "failed"
                        step_detail["healed_log"] = heal_fail_msg
                        success = False
                        final_message = f"Langkah {step_num} gagal dan tidak dapat dipulihkan oleh AI. Error: {str(err)}"
                        if ui_callback:
                            ui_callback(step_detail)
                        break

                if ui_callback:
                    ui_callback(step_detail)
                time.sleep(0.8)

        except Exception as e:
            success = False
            final_message = f"Gagal menjalankan pengujian dengan self-healing: {str(e)}"
        finally:
            if self.driver:
                self.driver.close()
                
        return {
            "success": success,
            "steps": steps_executed,
            "message": final_message
        }
