import re
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.services.model_engine.base import ExtractedFieldData
from app.pipeline.emirates_id_parser import validate_emirates_id_number, parse_date_string, normalize_arabic_digits

def run_validation_rules(
    document_type_code: str,
    fields: List[ExtractedFieldData],
    schema_definition: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Executes validation rules per document type and schema definition:
    - Enforces mandatory fields
    - Unparseable date = failed error
    - Runs schema rules (not_expired on any type, valid_eid_format, valid_trn_format = 15 digits starting 100)
    - Validates regex patterns and checks confidence_threshold
    """
    results: List[Dict[str, Any]] = []
    field_map: Dict[str, ExtractedFieldData] = {f.field_name: f for f in fields}

    # 1. Resolve schema fields and rules
    schema_fields = []
    schema_rules = []
    if schema_definition:
        schema_fields = schema_definition.get("fields", [])
        schema_rules = schema_definition.get("rules", []) or []

    # Default fallback for emirates_id if schema_definition is empty
    if not schema_fields and document_type_code == "emirates_id":
        schema_fields = [
            {"key": "id_number", "required": True, "confidence_threshold": 0.90, "validation_regex": r"^784-[0-9]{4}-[0-9]{7}-[0-9]{1}$"},
            {"key": "full_name_ar", "required": True, "confidence_threshold": 0.85},
            {"key": "full_name_en", "required": True, "confidence_threshold": 0.85},
            {"key": "expiry_date", "data_type": "date", "required": True, "confidence_threshold": 0.90},
            {"key": "date_of_birth", "data_type": "date", "required": True, "confidence_threshold": 0.85},
        ]
        if not schema_rules:
            schema_rules = [
                {"rule": "not_expired", "field": "expiry_date"},
                {"rule": "valid_eid_format", "field": "id_number"}
            ]

    # 2. Required Fields Check, Validation Regex, and Confidence Threshold
    for sf in schema_fields:
        f_key = sf.get("key") or sf.get("name")
        if not f_key:
            continue
        is_required = sf.get("required", False)
        data_type = sf.get("data_type", "string")
        conf_threshold = sf.get("confidence_threshold", 0.85)
        val_regex = sf.get("validation_regex")

        f = field_map.get(f_key)
        # Check alias (e.g. name_en vs full_name_en)
        if not f and f_key == "full_name_en":
            f = field_map.get("name_en")
        elif not f and f_key == "full_name_ar":
            f = field_map.get("name_ar")

        # 2a. Required check
        if is_required:
            if not f or not f.value:
                results.append({
                    "rule_name": f"REQUIRED_FIELD_{f_key.upper()}",
                    "field_name": f_key,
                    "passed": False,
                    "severity": "error",
                    "message": f"Mandatory field '{f_key}' was not detected in document."
                })
            else:
                results.append({
                    "rule_name": f"REQUIRED_FIELD_{f_key.upper()}",
                    "field_name": f_key,
                    "passed": True,
                    "severity": "info",
                    "message": f"Mandatory field '{f_key}' is present."
                })

        # 2b. Date format check (Unparseable date = failed error)
        if f and f.value and data_type == "date":
            parsed_dt = parse_date_string(f.value)
            if not parsed_dt:
                results.append({
                    "rule_name": f"DATE_FORMAT_{f_key.upper()}",
                    "field_name": f_key,
                    "passed": False,
                    "severity": "error",
                    "message": f"Date value '{f.value}' for '{f_key}' could not be parsed into a valid date format."
                })
            else:
                results.append({
                    "rule_name": f"DATE_FORMAT_{f_key.upper()}",
                    "field_name": f_key,
                    "passed": True,
                    "severity": "info",
                    "message": f"Date format verified ({parsed_dt})."
                })

        # 2c. Validation Regex
        if f and f.value and val_regex:
            cleaned_val = normalize_arabic_digits(f.value).strip()
            if not re.search(val_regex, cleaned_val):
                results.append({
                    "rule_name": f"REGEX_{f_key.upper()}",
                    "field_name": f_key,
                    "passed": False,
                    "severity": "error",
                    "message": f"Field '{f_key}' value '{f.value}' does not match required regex pattern '{val_regex}'."
                })
            else:
                results.append({
                    "rule_name": f"REGEX_{f_key.upper()}",
                    "field_name": f_key,
                    "passed": True,
                    "severity": "info",
                    "message": f"Field '{f_key}' format matches required regex."
                })

        # 2d. Confidence threshold check
        if f and f.value is not None:
            if f.confidence < conf_threshold:
                results.append({
                    "rule_name": f"CONFIDENCE_THRESHOLD_{f_key.upper()}",
                    "field_name": f_key,
                    "passed": False,
                    "severity": "warning",
                    "message": f"Field '{f_key}' confidence ({f.confidence:.2f}) is below threshold ({conf_threshold:.2f})."
                })
            else:
                results.append({
                    "rule_name": f"CONFIDENCE_THRESHOLD_{f_key.upper()}",
                    "field_name": f_key,
                    "passed": True,
                    "severity": "info",
                    "message": f"Field '{f_key}' meets confidence threshold."
                })

    # 3. Explicit Schema Rules & Document Type Specific Rules
    # Gather all rules to execute
    rules_to_run = list(schema_rules)

    # If emirates_id, ensure valid_eid_format and not_expired are present
    if document_type_code == "emirates_id":
        if not any(r.get("rule") == "valid_eid_format" for r in rules_to_run):
            rules_to_run.append({"rule": "valid_eid_format", "field": "id_number"})
        if not any(r.get("rule") == "not_expired" for r in rules_to_run):
            rules_to_run.append({"rule": "not_expired", "field": "expiry_date"})
        # Date of birth plausibility
        dob_f = field_map.get("date_of_birth")
        if dob_f and dob_f.value:
            parsed_dob = parse_date_string(dob_f.value)
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

    # If commercial_invoice, ensure valid_trn_format is present
    if document_type_code == "commercial_invoice":
        if not any(r.get("rule") == "valid_trn_format" for r in rules_to_run):
            rules_to_run.append({"rule": "valid_trn_format", "field": "trn"})

    for rule_spec in rules_to_run:
        rule_type = rule_spec.get("rule")
        target_field = rule_spec.get("field", "")
        f_entry = field_map.get(target_field)

        # Rule: not_expired (Any document type)
        if rule_type == "not_expired":
            if not f_entry or not f_entry.value:
                results.append({
                    "rule_name": f"NOT_EXPIRED_{target_field.upper()}",
                    "field_name": target_field,
                    "passed": False,
                    "severity": "error",
                    "message": f"Expiry date field '{target_field}' is missing or empty."
                })
            else:
                parsed_exp = parse_date_string(f_entry.value)
                if not parsed_exp:
                    results.append({
                        "rule_name": f"NOT_EXPIRED_{target_field.upper()}",
                        "field_name": target_field,
                        "passed": False,
                        "severity": "error",
                        "message": f"Expiry date '{f_entry.value}' could not be parsed into a valid date."
                    })
                else:
                    try:
                        exp_dt = datetime.strptime(parsed_exp, "%Y-%m-%d").date()
                        today = date.today()
                        if exp_dt < today:
                            results.append({
                                "rule_name": f"NOT_EXPIRED_{target_field.upper()}",
                                "field_name": target_field,
                                "passed": False,
                                "severity": "error",
                                "message": f"Document expired on {parsed_exp}. Current date is {today.isoformat()}."
                            })
                        else:
                            results.append({
                                "rule_name": f"NOT_EXPIRED_{target_field.upper()}",
                                "field_name": target_field,
                                "passed": True,
                                "severity": "info",
                                "message": f"Document expiry date {parsed_exp} is currently valid."
                            })
                    except Exception as e:
                        results.append({
                            "rule_name": f"NOT_EXPIRED_{target_field.upper()}",
                            "field_name": target_field,
                            "passed": False,
                            "severity": "error",
                            "message": f"Failed comparing expiry date: {e}"
                        })

        # Rule: valid_eid_format (784-YYYY-NNNNNNN-C with Luhn checksum)
        elif rule_type == "valid_eid_format":
            if not f_entry or not f_entry.value:
                results.append({
                    "rule_name": "EMIRATES_ID_FORMAT_AND_CHECKSUM",
                    "field_name": target_field,
                    "passed": False,
                    "severity": "error",
                    "message": "Emirates ID number is missing or not detected."
                })
            else:
                valid, formatted_id, expected_check = validate_emirates_id_number(f_entry.value)
                if not valid:
                    results.append({
                        "rule_name": "EMIRATES_ID_FORMAT_AND_CHECKSUM",
                        "field_name": target_field,
                        "passed": False,
                        "severity": "error",
                        "message": (
                            f"Emirates ID '{f_entry.value}' failed check-digit validation. "
                            f"Expected check digit: {expected_check}."
                        )
                    })
                else:
                    results.append({
                        "rule_name": "EMIRATES_ID_FORMAT_AND_CHECKSUM",
                        "field_name": target_field,
                        "passed": True,
                        "severity": "info",
                        "message": f"Emirates ID check digit verified successfully ({formatted_id})."
                    })

        # Rule: valid_trn_format (15 digits starting with 100)
        elif rule_type == "valid_trn_format":
            if not f_entry or not f_entry.value:
                results.append({
                    "rule_name": "VALID_TRN_FORMAT",
                    "field_name": target_field,
                    "passed": False,
                    "severity": "error",
                    "message": "TRN is missing or not detected."
                })
            else:
                digits_only = re.sub(r"\D", "", normalize_arabic_digits(f_entry.value))
                if len(digits_only) == 15 and digits_only.startswith("100"):
                    results.append({
                        "rule_name": "VALID_TRN_FORMAT",
                        "field_name": target_field,
                        "passed": True,
                        "severity": "info",
                        "message": f"TRN '{digits_only}' verified (15 digits starting with 100)."
                    })
                else:
                    results.append({
                        "rule_name": "VALID_TRN_FORMAT",
                        "field_name": target_field,
                        "passed": False,
                        "severity": "error",
                        "message": f"Invalid UAE TRN '{f_entry.value}': must be exactly 15 digits starting with 100."
                    })

    return results
