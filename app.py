import io
import os
import tempfile
from contextlib import redirect_stdout

from flask import Flask, after_this_request, render_template, request, send_file

from generate_stl import generate_stl_from_svg

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB


def _parse_float(form_value, label):
    try:
        return float(form_value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a valid number.")


@app.get("/")
def index():
    return render_template(
        "index.html",
        values={"thickness": "3.0", "tolerance": "-0.2", "density": "0.5"},
        error=None,
        logs="",
    )


@app.post("/generate")
def generate():
    upload = request.files.get("svg_file")
    if not upload or not upload.filename:
        return render_template(
            "index.html",
            values=request.form,
            error="Please select an SVG file.",
            logs="",
        ), 400

    if not upload.filename.lower().endswith(".svg"):
        return render_template(
            "index.html",
            values=request.form,
            error="Only .svg files are supported.",
            logs="",
        ), 400

    try:
        thickness = _parse_float(request.form.get("thickness"), "Thickness")
        tolerance = _parse_float(request.form.get("tolerance"), "Tolerance")
        density = _parse_float(request.form.get("density"), "Density")
    except ValueError as exc:
        return render_template(
            "index.html", values=request.form, error=str(exc), logs=""
        ), 400

    if thickness <= 0:
        return render_template(
            "index.html",
            values=request.form,
            error="Thickness must be greater than 0.",
            logs="",
        ), 400

    if density <= 0:
        return render_template(
            "index.html",
            values=request.form,
            error="Density must be greater than 0.",
            logs="",
        ), 400

    input_tmp = tempfile.NamedTemporaryFile(suffix=".svg", delete=False)
    output_tmp = tempfile.NamedTemporaryFile(suffix=".stl", delete=False)
    input_path = input_tmp.name
    output_path = output_tmp.name

    input_tmp.close()
    output_tmp.close()

    try:
        upload.save(input_path)
        logs = io.StringIO()
        with redirect_stdout(logs):
            generate_stl_from_svg(
                input_file=input_path,
                output_file=output_path,
                thickness=thickness,
                tolerance=tolerance,
                density=density,
            )

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            return render_template(
                "index.html",
                values=request.form,
                error="STL generation failed. Check SVG topology and parameters.",
                logs=logs.getvalue(),
            ), 400

        @after_this_request
        def cleanup(response):
            for path in (input_path, output_path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            return response

        source_name = os.path.splitext(upload.filename)[0]
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{source_name}.stl",
            mimetype="application/sla",
        )
    except Exception as exc:
        for path in (input_path, output_path):
            try:
                os.remove(path)
            except OSError:
                pass
        return render_template(
            "index.html",
            values=request.form,
            error=f"Generation failed: {exc}",
            logs="",
        ), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
