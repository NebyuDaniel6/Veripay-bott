    async def extract_data_basic_ocr(self, image_data: bytes) -> Dict[str, Any]:
        """Extract basic data from image using regex (fallback if Vision API fails)"""
        text = image_data.decode("utf-8", errors="ignore")  # Simple decode for basic text extraction
        logger.info(f"Basic OCR extracted text: {text}")

        amount_match = re.search(r"(\d[\d,]*\.?\d{0,2})\s*(ETB|BIRR)", text, re.IGNORECASE)
        amount = float(amount_match.group(1).replace(",", "")) if amount_match else 500.0

        transaction_id = f"OCR{len(transactions) + 1:06d}"
        date = datetime.now().strftime("%Y-%m-%d")
        time = datetime.now().strftime("%H:%M")
        payer = "Customer"
        receiver = "Restaurant"
        bank_name = self.detect_bank_name(text)
        payment_method = bank_name

        return {
            "amount": amount,
            "transaction_id": transaction_id,
            "date": date,
            "time": time,
            "payer": payer,
            "receiver": receiver,
            "bank_name": bank_name,
            "payment_method": payment_method,
            "currency": "ETB"
        }
