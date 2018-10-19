import SOLWEIG.PET_calculations as p
import SOLWEIG.UTCI_calculations as utci

ta = 20.
age = 35.
v = 6.
RH = 93.
sex = 1.
activity = 80.
mbody = 75.
tmrt = 40.494
ht = 1.80

clo = 0.9

# result = p._PET(ta,RH,tmrt,v,mbody,age,ht,activity,clo,sex)
result = utci.utci_calculator(ta, RH, tmrt, v)
print(result)