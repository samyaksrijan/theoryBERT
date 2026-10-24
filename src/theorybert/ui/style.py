CSS = """
<style>
/* Only app-owned classes and documented st.container(key=...) hooks. */
.tb-brand {display:flex;align-items:center;gap:12px;margin-bottom:7px;color:#17243B}
.tb-monogram {display:grid;place-items:center;width:35px;height:35px;background:#4F46A5;color:white;border-radius:10px;font-weight:700;font-size:19px}
.tb-brand h1 {font-size:28px;letter-spacing:-.8px;padding:0;margin:0;font-weight:700;line-height:1.3}
.tb-brand span.tb-tag {font-size:11px;letter-spacing:1.3px;text-transform:uppercase;color:#657185;margin-left:10px}
.tb-intro {color:#536176;font-size:16px;margin:0 0 28px 0;line-height:1.6}
.st-key-work-input,.st-key-work-result {background:#FFFFFF;border-radius:16px;border:1px solid #E1E3E8;padding:24px}
.tb-section {display:flex;align-items:center;gap:10px;margin:0 0 15px;font-size:17px;font-weight:650;color:#17243B}
.tb-step {font-size:12px;font-weight:600;color:#4F46A5;background:#EFEDF9;padding:5px 8px;border-radius:6px}
.tb-kicker {font-size:11px;letter-spacing:1.3px;font-weight:650;text-transform:uppercase;color:#657185;margin-bottom:8px}
.tb-status {border:1px solid #DFE3EA;background:#F8F9FC;padding:15px 17px;border-radius:10px;margin-bottom:14px;line-height:1.5}
.tb-status strong {display:block;font-size:15px;font-weight:650}
.tb-status span {display:block;font-size:13px;margin-top:3px;color:#536176}
.tb-status.verified {background:#F0F8F3;border-color:#CCE5D5;color:#246342}
.tb-status.failed {background:#FFF3F3;border-color:#EECFD1;color:#9C3341}
.tb-status.pending {background:#FFFAEF;border-color:#EBDDAD;color:#815F16}
.tb-empty {border:1px dashed #DADDE7;border-radius:12px;background:#FCFCFA;min-height:300px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:30px 24px;margin-bottom:16px}
.tb-empty h3 {font-size:20px;font-weight:600;margin:12px 0 8px;color:#17243B}
.tb-empty p {font-size:14px;line-height:1.7;color:#647084;max-width:380px;margin:0}
.tb-empty .tb-symbol {font-size:30px;letter-spacing:8px;color:#9691BC;font-family:monospace}
.tb-meta {font-size:13px;color:#536176;line-height:1.7;margin-bottom:12px;overflow-wrap:anywhere}
.tb-foot {margin:24px 0 6px;border-top:1px solid #DFE2E7;padding-top:16px;font-size:12px;color:#647084;line-height:1.7}
.tb-pipeline {font-size:12px;color:#657185;margin:4px 0 14px;letter-spacing:.1px}
.tb-pipeline b {color:#4F46A5}
.tb-token {display:inline-block;border:1px solid #E0E3EB;border-radius:6px;padding:3px 8px;margin:2px;font-family:monospace;color:#536176}
.tb-token.current {border-color:#4F46A5;background:#EEECF8;color:#4F46A5;font-weight:bold}
.tb-explanation {font-size:14px;line-height:1.6;color:#17243B;padding:12px 14px;border-left:3px solid #4F46A5;background:#F7F6FC;border-radius:0 8px 8px 0;margin:8px 0 12px;overflow-wrap:anywhere}
@media(max-width:640px){.st-key-work-input,.st-key-work-result{padding:17px}.tb-brand span.tb-tag{display:none}.tb-intro{font-size:14px;margin-bottom:18px}.tb-brand h1{font-size:25px}.tb-empty{min-height:230px;padding:20px 14px}}
</style>
"""
