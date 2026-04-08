def eligibility_grader(output, expected=None):
    # simple deterministic scoring
    score = 0.6
    return min(max(score, 0.01), 0.99)


def ae_grader(output, expected=None):
    score = 0.7
    return min(max(score, 0.01), 0.99)


def protocol_grader(output, expected=None):
    score = 0.8
    return min(max(score, 0.01), 0.99)