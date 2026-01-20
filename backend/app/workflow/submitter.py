"""
Workflow orchestration for form submissions
Coordinates between AI (BRAIN) and Automation (HANDS)
"""
from app.automation.browser import BrowserAutomation
from app.ai.form_reader import FormReader
from app.utils.logger import logger


class SubmissionWorkflow:
    """
    Orchestrates the submission workflow
    """
    
    def __init__(self):
        self.browser = BrowserAutomation()
        self.form_reader = FormReader()
    
    async def submit_form(self, saas_url: str, form_data: dict) -> dict:
        """
        Complete workflow for form submission:
        1. Navigate to form
        2. Analyze form with AI
        3. Map data to form fields
        4. Fill and submit form
        5. Verify submission
        """
        try:
            logger.info(f"Starting submission workflow for {saas_url}")
            
            # Step 1: Navigate to form
            await self.browser.navigate(saas_url)
            
            # Step 2: Get form HTML and analyze with AI
            html_content = await self.browser.page.content()
            form_structure = await self.form_reader.analyze_form(html_content)
            
            # Step 3: Map data to form fields
            mapped_data = await self.form_reader.map_data_to_form(form_structure, form_data)
            
            # Step 4: Fill and submit form
            await self.browser.fill_form(mapped_data)
            await self.browser.submit_form()
            
            # Step 5: Verify submission (optional)
            # await self.verify_submission()
            
            logger.info("Submission workflow completed successfully")
            return {"status": "success", "message": "Form submitted successfully"}
            
        except Exception as e:
            logger.error(f"Submission workflow failed: {str(e)}")
            return {"status": "error", "message": str(e)}
        
        finally:
            await self.browser.close()
