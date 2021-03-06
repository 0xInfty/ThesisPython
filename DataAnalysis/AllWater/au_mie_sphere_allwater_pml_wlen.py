#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 11 12:24:04 2020

@author: vall
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.pylab as plab
import os
import PyMieScatt as ps
import v_analysis as va
from v_materials import import_medium
import v_save as vs
import v_utilities as vu

#%% PARAMETERS

# Saving directories
folder = ["AuMieMediums/AllWaterTest/9)BoxDimensions/PMLWlen"]
home = vs.get_home()

# Sorting and labelling data series
sorting_function = [lambda l : vu.sort_by_number(l, -2)]
# def special_label(s):
#     if "5" in s:
#         return "Mie"
#     else:
#         return ""
series_label = [lambda s : f"PML-$\lambda$ factor {vu.find_numbers(s)[-2]:.2f}"]
series_must = [""] # leave "" per default
series_mustnt = [""] # leave "" per default
series_column = [1]

# Scattering plot options
plot_title = "Au 103 nm sphere in water"
series_colors = [plab.cm.Reds]
series_linestyles = ["solid"]
plot_make_big = False
plot_file = lambda n : os.path.join(home, "DataAnalysis/PMLWlen" + n)

#%% LOAD DATA

path = []
file = []
series = []
data = []
params = []
header = []

for f, sf, sm, smn in zip(folder, sorting_function, series_must, series_mustnt):

    path.append( os.path.join(home, f) )
    file.append( lambda f, s : os.path.join(path[-1], f, s) )
    
    series.append( os.listdir(path[-1]) )
    series[-1] = vu.filter_by_string_must(series[-1], sm)
    if smn!="": series[-1] = vu.filter_by_string_must(series[-1], smn, False)
    series[-1] = sf(series[-1])
    
    data.append( [] )
    params.append( [] )
    for s in series[-1]:
        data[-1].append(np.loadtxt(file[-1](s, "Results.txt")))
        params[-1].append(vs.retrieve_footer(file[-1](s, "Results.txt")))
    header.append( vs.retrieve_header(file[-1](s, "Results.txt")) )
    
    for i in range(len(params[-1])):
        if not isinstance(params[-1][i], dict): 
            params[-1][i] = vu.fix_params_dict(params[-1][i])
    
r = []
from_um_factor = []
flux_box_size = []
sysname = []
for par in params:
    r.append([p["r"] for p in par])
    from_um_factor.append([p["from_um_factor"] for p in par])
    flux_box_size.append([p["flux_box_size"] for p in par])
    sysname.append([p["sysname"] for p in par])

#%% LOAD MIE DATA

from_um_factor = params[0][0]["from_um_factor"]
wlen_range = params[0][0]["wlen_range"]
r = params[0][0]["r"]
index = params[0][0]["submerged_index"]

medium = import_medium("Au", from_um_factor, paper="JC")

wlens = data[0][-1][:,0]
freqs = 1e3*from_um_factor/wlens
scatt_eff_theory = [ps.MieQ(np.sqrt(medium.epsilon(f)[0,0]*medium.mu(f)[0,0]), 
                            1e3*from_um_factor/f,
                            2*r*1e3*from_um_factor,
                            nMedium=index,
                            asDict=True)['Qsca'] 
                    for f in freqs]
scatt_eff_theory = np.array(scatt_eff_theory)

#%% GET MAX WAVELENGTH

max_wlen = []
for d, sc in zip(data, series_column):
    max_wlen.append( [d[i][np.argmax(d[i][:,sc]), 0] for i in range(len(d))] )
max_wlen_theory = wlens[np.argmax(scatt_eff_theory)]

dif_max_wlen = [ml - max_wlen_theory for ml in max_wlen[0]]

#%% WAVELENGTH MAXIMUM DIFFERENCE VS WAVELENGTH MAXIMUM

pml_wlen_factor = [vu.find_numbers(s)[0] for s in series[0]]
pml_width_nm = [p["pml_width"]*p["from_um_factor"]*1e3 for p in params[0]]

fig = plt.figure()
plt.title("Difference in scattering maximum for " + plot_title)
plt.plot(pml_wlen_factor, dif_max_wlen, '.', markersize=12)
plt.xlabel("PML width as multiples of maximum of $\lambda$ range")
plt.grid(True)
ax2 = plt.twiny()
ax2.plot(pml_width_nm, dif_max_wlen, '.', markersize=12)
# ax2.set_xlim(np.array( fig.axes[0].get_xlim() ) * params[0][0]["from_um_factor"] * 1e3 )
plt.xlabel("PML width [nm]")
plt.ylabel("Difference in wavelength $\lambda_{max}^{MEEP}-\lambda_{max}^{MIE}$ [nm]")
vs.saveplot(plot_file("WLenDiff.png"), overwrite=True)

#%% GET ENLAPSED TIME COMPARED

pml_wlen_factor = [[vu.find_numbers(s)[0] for s in ser] for ser in series]
enlapsed_time = [[p["enlapsed"] for p in par] for par in params]
total_enlapsed_time = [[sum(p["enlapsed"]) for p in par] for par in params]

first_pml_wlen_factor = []
second_pml_wlen_factor = []
first_build_time = []
first_sim_time = []
second_flux_time = []
second_build_time = []
second_sim_time = []
for enl, pmlwl in zip(enlapsed_time, pml_wlen_factor):
    first_pml_wlen_factor.append( [] )
    first_build_time.append( [] )
    first_sim_time.append( [] )
    second_pml_wlen_factor.append( [] )
    second_flux_time.append( [] )
    second_build_time.append( [] )
    second_sim_time.append( [] )
    for e, pwl in zip(enl, pmlwl):
        if len(e)==5:
            first_pml_wlen_factor[-1].append( pwl )
            second_pml_wlen_factor[-1].append( pwl )
            first_build_time[-1].append( e[0] )
            first_sim_time[-1].append( e[1] )
            second_build_time[-1].append( e[2] )
            second_flux_time[-1].append( e[3] )
            second_sim_time[-1].append( e[4] )
        elif len(e)==3:
            second_pml_wlen_factor[-1].append( pwl )
            second_build_time[-1].append( e[0] )
            second_flux_time[-1].append( e[1] )
            second_sim_time[-1].append( e[2] )
        else:
            print(f"Unknown error in pml_wlen_factor {pwl} of", pmlwl)

plt.figure()
plt.title("Enlapsed total time for simulation of " + plot_title)
for pmlwl, tot in zip(pml_wlen_factor, total_enlapsed_time):
    plt.plot(pmlwl, tot, '.', markersize=12)
plt.legend(["Meep R", "Meep JC"], loc="lower right")
plt.xlabel("PML width as multiples of maximum of $\lambda$ range")
plt.ylabel("Enlapsed time [s]")
vs.saveplot(plot_file("ComparedTotTime.png"), overwrite=True)
        
plt.figure()
plt.title("Enlapsed time for simulations of " + plot_title)
plt.plot(first_pml_wlen_factor[0], first_sim_time[0], 'D-', color="r", label="Sim I")
plt.plot(second_pml_wlen_factor[0], second_sim_time[0], 's-', color="r", label="Sim II")
plt.xlabel("PML width as multiples of maximum of $\lambda$ range")
plt.ylabel("Enlapsed time in simulations [s]")
plt.legend()
plt.savefig(plot_file("ComparedSimTime.png"), bbox_inches='tight')

plt.figure()
plt.title("Enlapsed time for building of " + plot_title)
plt.plot(first_pml_wlen_factor[0], first_build_time[0], 'D-', color="b", label="Sim I")
plt.plot(second_pml_wlen_factor[0], second_build_time[0], 's-', color="b", label="Sim II")
plt.xlabel("PML width as multiples of maximum of $\lambda$ range")
plt.ylabel("Enlapsed time in building [s]")
plt.legend()
plt.savefig(plot_file("ComparedBuildTime.png"), bbox_inches='tight')

plt.figure()
plt.title("Enlapsed time for loading flux of " + plot_title)
plt.plot(second_pml_wlen_factor[0], second_flux_time[0], 's-', color="m", label="Sim II")
plt.xlabel("PML width as multiples of maximum of $\lambda$ range")
plt.ylabel("Enlapsed time in loading flux [s]")
plt.savefig(plot_file("ComparedLoadTime.png"), bbox_inches='tight')

#%% PLOT NORMALIZED

colors = [sc(np.linspace(0,1,len(s)+3))[3:] 
          for sc, s in zip(series_colors, series)]

plt.figure()
plt.title("Normalized scattering for " + plot_title)
for s, d, p, sc, psl, pc, pls in zip(series, data, params, series_column, 
                                     series_label, colors, series_linestyles):

    for ss, sd, sp, spc in zip(s, d, p, pc):
        index_argmax = np.argmax(abs(sd[:,sc]))
        plt.plot(sd[:,0], sd[:,sc] / sd[index_argmax, sc], 
                 linestyle=pls, color=spc, label=psl(ss))

plt.plot(wlens, scatt_eff_theory / max(scatt_eff_theory), 
         linestyle="dashed", color='red', label="Mie Theory")
plt.xlabel("Wavelength [nm]")
plt.ylabel("Normalized Scattering Cross Section")
plt.legend()
if plot_make_big:
    mng = plt.get_current_fig_manager()
    mng.window.showMaximized()
    del mng
vs.saveplot(plot_file("AllScattNorm.png"), overwrite=True)

#%% PLOT IN UNITS

colors = [sc(np.linspace(0,1,len(s)+3))[3:] 
          for sc, s in zip(series_colors, series)]

plt.figure()
plt.title("Scattering for " + plot_title)
for s, d, p, sc, psl, pc, pls in zip(series, data, params, series_column, 
                                     series_label, colors, series_linestyles):

    for ss, sd, sp, spc in zip(s, d, p, pc):
        sign = np.sign( sd[ np.argmax(abs(sd[:,sc])), sc ] )
        plt.plot(sd[:,0], sign * sd[:,sc] * np.pi * (sp["r"] * sp["from_um_factor"] * 1e3)**2,
                 linestyle=pls, color=spc, label=psl(ss))
            
plt.plot(wlens, scatt_eff_theory  * np.pi * (sp["r"] * sp["from_um_factor"] * 1e3)**2,
         linestyle="dashed", color='red', label="Mie Theory")
plt.xlabel("Wavelength [nm]")
plt.ylabel(r"Scattering Cross Section [nm$^2$]")
plt.legend()
if plot_make_big:
    mng = plt.get_current_fig_manager()
    mng.window.showMaximized()
    del mng
vs.saveplot(plot_file("AllScatt.png"), overwrite=True)