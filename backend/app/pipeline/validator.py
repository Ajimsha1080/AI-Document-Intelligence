from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.services.model_engine.base import ExtractedFieldData
from app.pipeline.emirates_id_parser import validate_emirates_id_number, parse_date_string

def run_validation_rules(
    document_type_code: str,
    fields: List[ExtractedFieldData],
    schema_definition: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Executes validation rules per document type.
    Returns list of validation outcomes with associated field name and severity.
    """
    results = []
    field_map: Dict[str, ExtractedFieldData] = {f.field_name: f for f in fields}

    # 1. Required Fields Check
    required_fields = []
    if schema_definition and "fields" in schema_definition:
        required_fields = [
            f["name"] for f in schema_definition["fields"] if f.get("required", False)
        ]
    elif document_type_code == "emirates_id":
        required_fields = ["id_number", "full_name_ar", "full_name_en", "expiry_date"]

    for rf in required_fields:
        f = field_map.get(rf)
        if not f or not f.value:
            results.append({
                "rule_name": f"REQUIRED_FIELD_{rf.upper()}",
                "field_name": rf,
                "passed": False,
                "severity": "error",
                "message": f"Mandatory field '{rf}' was not detected in document."
            })
        else:
            results.append({
                "rule_name": f"REQUIRED_FIELD_{rf.upper()}",
                "field_name": rf,
                "passed": True,
                "severity": "info",
                "message": f"Mandatory field '{rf}' is present."
            })

    # 2. Emirates ID specific rules
    if document_type_code == "emirates_id":
        id_field = field_map.get("id_number")
        if id_field and id_field.value:
            valid, formatted_id, expected_check = validate_emirates_id_number(id_field.value)
            if not valid:
                results.append({
                    "rule_name": "EMIRATES_ID_FORMAT_AND_CHECKSUM",
                    "field_name": "id_number",
                    "passed": False,
                    "severity": "error",
                    "message": (
                        f"Emirates ID '{id_field.value}' failed standard check-digit validation. "
                        f"Expected check digit: {expected_check}."
                    )
                })
            else:
                results.append({
                    "rule_name": "EMIRATES_ID_FORMAT_AND_CHECKSUM",
                    "field_name": "id_number",
                    "passed": True,
                    "severity": "info",
                    "message": f"Emirates ID check digit verified successfully ({formatted_id})."
                })

        # Expiry date not past
        exp_field = field_map.get("expiry_date")
        if exp_field and exp_field.value:
            parsed_exp = parse_date_string(exp_field.value)
            if parsed_exp:
                try:
                    exp_dt = datetime.strptime(parsed_exp, "%Y-%m-%d").date()
                    today = date.today()
                    if exp_dt < today:
                        results.append({
                            "rule_name": "EXPIRY_DATE_VALIDITY",
                            "field_name": "expiry_date",
                            "passed": False,
                            "severity": "error",
                            "message": f"Document expired on {parsed_exp}. Current date is {today.isoformat()}."
                        })
                    else:
                        results.append({
                            "rule_name": "EXPIRY_DATE_VALIDITY",
                            "field_name": "expiry_date",
                            "passed": True,
                            "severity": "info",
                            "message": f"Document expiry date {parsed_exp} is currently valid."
                        })
                except Exception:
                    pass

        # Birth date plausible (birth date must be in the past)
        dob_field = field_map.get("date_of_birth")
        if dob_field and dob_field.value:
            parsed_dob = parse_date_string(dob_field.value)
            if parsed_dob:
                try:
                    dob_dt = datetime.strptime(parsed_dob, "%Y-%m-%d").date()
                    if dob_dt >= date.today():
                        results.append({
                            "rule_name": "DATE_OF_BIRTH_PLAUSIBILITY",
                            "field_name": "date_of_birth",
                            "passed": False,
                            "severity": "error",
                            "message": f"Date of birth {parsed_dob} cannot be in the future."
                        })
                    else:
                        results.append({
                            "rule_name": "DATE_OF_BIRTH_PLAUSIBILITY",
                            "field_name": "date_of_birth",
                            "passed": True,
                            "severity": "info",
                            "message": "Date of birth is valid."
                        })
                except Exception:
                    pass

    return results
