def constraint_TM(v1, x1, v2, x2):
    e1, d1 = v1[1:].split(',')
    e2, d2 = v2[1:].split(',')
    d1 = int(d1)
    d2 = int(d2)

    if e1 != e2:
        return True    
    if d1 == d2:
        return x1 != x2
    if abs(d1 - d2) != 1:
        return True
    if d1 > d2 and x2 == "T":
        return x1 != "M"
    if d1 < d2 and x1 == "T":
        return x2 != "M"
    return True