from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import GeneratedReport, User


class ReportService:
    async def create_report(
        self,
        session: AsyncSession,
        user: User,
        report_type: str,
        title: str,
        body: str,
    ) -> GeneratedReport:
        output_dir = Path("backend/static/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{user.id}_{report_type}.pdf"

        pdf = canvas.Canvas(str(file_path), pagesize=A4)
        width, height = A4
        pdf.setTitle(title)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(48, height - 72, title)
        pdf.setFont("Helvetica", 11)
        y = height - 112
        for line in body.splitlines() or [body]:
            pdf.drawString(48, y, line[:110])
            y -= 18
            if y < 72:
                pdf.showPage()
                y = height - 72
        pdf.save()

        report = GeneratedReport(
            user_id=user.id,
            report_type=report_type,
            title=title,
            file_path=str(file_path),
            status="ready",
        )
        session.add(report)
        return report
