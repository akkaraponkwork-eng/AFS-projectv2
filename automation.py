import random
import time
from playwright.sync_api import sync_playwright

import json
import os

def run_automation(username, password, temp_min, temp_max, start_row, end_row, time_period, show_browser=True, u_value='skip', state=None):
    if state is None:
        state = {"should_stop": False}
        
    def log(msg, type="info"):
        return json.dumps({"type": type, "message": msg}) + "\n"

    # ถ้าทำงานบน Server ของ Render บังคับให้เป็นแบบซ่อนหน้าจอ (เพราะเซิร์ฟเวอร์ไม่มีหน้าจอ)
    if os.environ.get('RENDER') == 'true':
        show_browser = False

    with sync_playwright() as p:
        yield log("กำลังเปิดเบราว์เซอร์...")
        # เปิด/ปิดหน้าจอเบราว์เซอร์ตามที่ผู้ใช้เลือกในหน้าเว็บ (หรือบังคับซ่อนบน Server)
        browser = p.chromium.launch(headless=not show_browser)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        # Auto-accept any native browser dialogs (alert, confirm, prompt)
        page.on("dialog", lambda dialog: dialog.accept())
        
        try:
            yield log("กำลังเข้าสู่หน้าล็อกอิน...")
            page.goto("https://rtamed.rta.mi.th:8443/login")
            page.wait_for_selector('input')
            
            if state.get("should_stop"):
                yield log("ยกเลิกการทำงาน", "warning")
                return
                
            inputs = page.locator('input').all()
            if len(inputs) >= 2:
                inputs[0].fill(username)
                inputs[1].fill(password)
                yield log("กรอกชื่อผู้ใช้และรหัสผ่านเรียบร้อย")
            else:
                yield log("ไม่พบช่องกรอกชื่อผู้ใช้และรหัสผ่าน", "error")
                return
            
            yield log("กำลังกดเข้าสู่ระบบ...")
            page.locator('button').click()
            page.wait_for_timeout(3000)
            
            if state.get("should_stop"):
                yield log("ยกเลิกการทำงาน", "warning")
                return
                
            yield log("กำลังไปยังเมนู 'การคัดกรอง'...")
            page.get_by_text("การคัดกรอง").click()
            page.wait_for_timeout(2000)
            
            processed = 0
            yield log(f"เริ่มดำเนินการตั้งแต่ลำดับที่ {start_row} ถึง {end_row}")
            
            target_row = start_row
            
            while target_row <= end_row:
                if state.get("should_stop"):
                    yield log("ยกเลิกการทำงาน", "warning")
                    break
                    
                rows = page.locator('tbody tr').all()
                if not rows:
                    yield log("ไม่พบข้อมูลตารางในหน้านี้", "warning")
                    break
                    
                found_on_page = False
                
                for row_idx, row in enumerate(rows):
                    if target_row > end_row:
                        break
                        
                    if state.get("should_stop"):
                        break
                        
                    # Get the row number from the first column
                    try:
                        first_col_text = row.locator('td').first.inner_text().strip()
                        row_num = int(first_col_text)
                    except Exception:
                        continue # Skip header or invalid rows
                        
                    if row_num == target_row:
                        target_temp = round(random.uniform(temp_min, temp_max), 1)
                        
                        # --- Real interaction ---
                        try:
                            time_offset = 1 if time_period == 'morning' else (2 if time_period == 'afternoon' else 3)
                            
                            # 🎯 เลื่อนหน้าจอไปยังแถวที่กำลังทำงานให้เห็นชัดเจน
                            row.scroll_into_view_if_needed()
                            page.wait_for_timeout(200) # รอให้เลื่อนเสร็จแป๊บนึง
                            
                            # ==== ส่วนของการกรอก U ====
                            if u_value != 'skip':
                                # ค้นหาช่องที่มีคำว่า 'U' ตรงๆ
                                u_cell = row.locator("td:text-is('U'), th:text-is('U')").first
                                if u_cell.count() == 0:
                                    # Fallback เผื่อมีช่องว่างหรือโครงสร้างซ้อน
                                    u_cell = row.locator("td, th").filter(has_text="U").last
                                
                                if u_cell.count() > 0:
                                    u_sibling_cells = u_cell.locator("~ td, ~ th")
                                    if u_sibling_cells.count() >= time_offset:
                                        target_u_cell = u_sibling_cells.nth(time_offset - 1)
                                        target_u_cell.click(force=True)
                                        actual_u = str(random.randint(0, 4)) if u_value == 'random' else u_value
                                        page.wait_for_timeout(500) # รอ Popup โหลด
                                        u_popup = page.locator("ngb-popover-window, .popover").last
                                        if u_popup.is_visible():
                                            u_popup.get_by_text(actual_u, exact=True).click()
                                            yield log(f"[{target_row}] กรอกค่า U={actual_u} เรียบร้อย", "info")
                                        else:
                                            yield log(f"[{target_row}] ไม่พบ Popup สำหรับกรอกค่า U", "warning")
                                        page.wait_for_timeout(300)
                                    else:
                                        yield log(f"[{target_row}] ไม่พบช่องตารางสำหรับกรอก U (เวลา: {time_period})", "warning")
                                else:
                                    yield log(f"[{target_row}] ไม่พบป้าย 'U' ในหน้านี้", "warning")
                            next_row = page.locator('tbody tr').nth(row_idx + 1)
                            
                            # The columns in the T row are: 0: 'T', 1: morning, 2: afternoon, 3: night, etc.
                            target_td = next_row.locator('td').nth(time_offset)
                            
                            # Click the cell (or the button inside it)
                            target_td.click()
                            
                            # Wait for the popup to appear
                            popup = page.locator("ngb-popover-window, .popover").last
                            popup.wait_for(state="visible", timeout=5000)
                            
                            # Click the whole number
                            popup.get_by_text(str(int(target_temp)), exact=True).click()
                            
                            # Give a tiny pause for UI to react
                            page.wait_for_timeout(300)
                            
                            # Click the decimal part if popup is still open
                            if popup.is_visible():
                                decimal_part = int(round((target_temp - int(target_temp)) * 10))
                                if decimal_part == 0:
                                    # ถ้า .0 ให้กดเลขเดิมซ้ำ
                                    popup.get_by_text(str(int(target_temp)), exact=True).click(timeout=2000)
                                else:
                                    popup.get_by_text(f".{decimal_part}", exact=True).click(timeout=2000)
                            
                        except Exception as e:
                            yield log(f"เกิดข้อผิดพลาดในการคลิกอุณหภูมิลำดับที่ {row_num}: {str(e)}", "warning")
                        
                        processed += 1
                        yield log(f"[{processed}] กรอกอุณหภูมิ {target_temp} สำหรับลำดับที่ {row_num} เรียบร้อย")
                        page.wait_for_timeout(500)
                        
                        target_row += 1
                        found_on_page = True
                
                if state.get("should_stop"):
                    break
                
                # If we made edits on this page, save them before moving to next page
                if found_on_page:
                    yield log("กำลังค้นหาปุ่มบันทึกข้อมูลสำหรับหน้านี้...")
                    try:
                        # Use a more flexible selector to find buttons containing 'บันทึก'
                        save_btn = page.locator("button:has-text('บันทึก')")
                        
                        # If it's not a button tag, try finding any element with the text
                        if save_btn.count() == 0:
                            save_btn = page.locator(":text-matches('บันทึก')").last
                        
                        if save_btn.count() > 0:
                            save_btn.first.click()
                            yield log("กดปุ่มบันทึกประจำหน้าเรียบร้อยแล้ว กำลังตรวจสอบหน้าต่างยืนยัน...")
                            page.wait_for_timeout(1500) # Wait for modal to pop up
                            
                            # Try to click "ตกลง" in the popup modal
                            # Scope to ngb-modal-window to prevent clicking a button behind the modal
                            confirm_btn = page.locator("ngb-modal-window button:has-text('ตกลง')")
                            if confirm_btn.count() == 0:
                                confirm_btn = page.locator("button:has-text('ตกลง')").last
                                
                            if confirm_btn.count() > 0 and confirm_btn.first.is_visible():
                                confirm_btn.first.click()
                                yield log("กดปุ่ม 'ตกลง' เพื่อยืนยันเรียบร้อยแล้ว")
                                
                            # If another "ตกลง" or "OK" appears (e.g. success message)
                            page.wait_for_timeout(1000)
                            success_btn = page.locator("ngb-modal-window button:has-text('ตกลง')")
                            if success_btn.count() == 0:
                                success_btn = page.locator("button:has-text('ตกลง')").last
                                
                            if success_btn.count() > 0 and success_btn.first.is_visible():
                                success_btn.first.click()
                                yield log("กดปุ่ม 'ตกลง' (รับทราบ) เรียบร้อยแล้ว")
                                
                            page.wait_for_timeout(2000) # Wait for save to complete
                        else:
                            yield log("ไม่พบปุ่มบันทึกในหน้านี้", "warning")
                    except Exception as e:
                        yield log(f"ไม่สามารถกดปุ่มบันทึก/ตกลงได้: {str(e)}", "warning")
                        
                # Check if we need to go to next page
                if target_row <= end_row:
                    yield log("กำลังเปลี่ยนไปยังหน้าถัดไป...")
                    try:
                        # 1. Try to click the page number immediately following the active page
                        next_page_number = page.locator(".pagination .active + li a, .pagination .active + .page-item .page-link").first
                        
                        if next_page_number.count() > 0:
                            next_page_number.click()
                            page.wait_for_timeout(2000)
                        else:
                            # 2. Try the "Next" arrow (›) or text
                            next_btn = page.locator("a:has-text('›'), a:has-text('Next'), a:has-text('ถัดไป'), [aria-label='Next'], [aria-label='ถัดไป']")
                            if next_btn.count() > 0:
                                next_btn.first.click()
                                page.wait_for_timeout(2000)
                            else:
                                yield log("ไม่พบปุ่มหน้าถัดไป หรือถึงหน้าสุดท้ายแล้ว")
                                break
                    except Exception as e:
                        yield log(f"เกิดข้อผิดพลาดในการเปลี่ยนหน้า: {str(e)}", "warning")
                        break

            yield log(f"ทำงานเสร็จสิ้นทั้งหมด {processed} รายการ!", "success")

        except Exception as e:
            yield log(f"เกิดข้อผิดพลาด: {str(e)}", "error")
        finally:
            browser.close()
