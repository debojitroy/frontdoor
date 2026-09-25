---
license: mit
task_categories:
- text-classification
language:
- en
pretty_name: sunny thakur
size_categories:
- n<1K
---
# Phishing and Benign Email Dataset

This dataset contains a curated collection of **phishing and legitimate (benign) emails** for use in cybersecurity training, phishing detection models, and email classification systems. Each entry is structured with subject, body, intent, technique, target, and classification label.

---

## 📁 Dataset Format

The dataset is stored in `.jsonl` (JSON Lines) format. Each line is a standalone JSON object.

### Fields:

| Field           | Description |
|------------------|-------------|
| `id`             | Unique email ID |
| `subject`        | Email subject line |
| `body`           | Full email content |
| `intent`         | Purpose of the email (e.g., credential harvesting, malware delivery) |
| `technique`      | Social engineering or technical trick used |
| `target`         | Who or what is being impersonated |
| `spoofed_sender` | Forged email address |
| `label`          | `"phishing"` or `"benign"` |

---

## 🔍 Example Entry

```json
{
  "id": "phish-0003",
  "subject": "Unusual Activity Detected",
  "body": "Suspicious login from Russia. Reset password now: https://g00gle-security.com",
  "intent": "Credential Harvesting",
  "technique": "Homoglyph Link Spoofing",
  "target": "Google",
  "spoofed_sender": "no-reply@g00gle.com",
  "label": "phishing"
}
✅ Use Cases

    Train NLP models to detect phishing content

    Classify or filter email threats in spam filters

    Educate users and red teams on phishing techniques

    Simulate email-based social engineering scenarios

📊 Dataset Summary

    🔐 Phishing Emails: ~100 entries

    ✅ Benign Emails: ~100 entries

    ⚖️ Balanced and ready for binary classification or LLM pretraining

⚠️ Disclaimer

This dataset is for research and educational purposes only. Do not use these emails in live environments. The authors are not responsible for misuse.
📜 License

This dataset is released under the MIT License.
📫 Contributions

Feel free to submit pull requests to add more phishing or legit emails. The more diverse, the better for training secure systems.