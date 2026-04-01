

def compute_alt_risk_score(duplicate, vpn_detected, discord_account_count, vm_detected=False):
    score = 10
    if duplicate:
        score += 35
    if vpn_detected:
        score += 20
    if discord_account_count > 1:
        score += 25
    if vm_detected:
        score += 15
    if score > 100:
        score = 100
    return score
