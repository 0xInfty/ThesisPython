# -*- coding: utf-8 -*-

# Adapted from Meep Tutorial: Mie Scattering of a Lossless Dielectric Sphere

# Scattering efficiency in visible spectrum of 120nm-diameter Au sphere.

from socket import gethostname
if "Nano" in gethostname():
    syshome = "/home/nanofisica/Documents/Vale/ThesisPython"
elif "vall" in gethostname():
    syshome = "/home/vall/Documents/Thesis/ThesisPython"
else:
    raise ValueError("Your PC must be registered at the top of this code")

import sys
sys.path.append(syshome)

import click as cli
import meep as mp
import numpy as np
import matplotlib.pyplot as plt
import os
from time import time
from v_materials import import_medium
import v_save as vs
import v_utilities as vu
# from v_units import MeepUnitsManager

#%% COMMAND LINE FORMATTER

@cli.command()
@cli.option("--series", "-s", type=str, 
            help="Series name used to create a folder and save files")
@cli.option("--folder", "-f", type=str, 
            help="Series folder used to save files")
@cli.option("--resolution", "-res", required=True, type=int,
            help="Spatial resolution. Number of divisions of each Meep unit")
# >=8 pixels per smallest wavelength, i.e. np.floor(8/wvl_min)
@cli.option("--from-um-factor", "-fum", "from_um_factor", 
            default=10e-3, type=float,
            help="Conversion of 1 μm to my length unit (i.e. 10e-3=10nm/1μm)")
@cli.option("--radius", "-r", "r", default=60, type=float,
            help="Radius of sphere expressed in nm")
@cli.option("--displacement", "-dis", "displacement", default=0, type=float,
            help="Overlap of sphere and surface in nm")
@cli.option("--paper", "-pp", "paper", type=str, default="R",
            help="Source of inner material experimental data. Options: 'JC'/'R'/'P'")
@cli.option("--submerged-index", "-sbi", "submerged_index", 
            type=float, default=1.33,
            help="Reflective index of sourrounding medium")
@cli.option("--surface-index", "-sfi", "surface_index", 
            type=float, default=1.54,
            help="Reflective index of surface medium")
@cli.option("--wlen-range", "-wr", "wlen_range", 
            type=vu.NUMPY_ARRAY, default="np.array([500,650])",
            help="Wavelength range expressed in nm")
# 500-650 nm range from lowest to highest
@cli.option("--second-time-factor", "-sectime", "second_time_factor", 
            type=float, default=10,
            help="How much longer should the 2nd simulation be than the 1st")
def main(series, folder, resolution, from_um_factor, r, displacement, paper,
         submerged_index, surface_index, wlen_range, second_time_factor):

    #%% PARAMETERS
    
    ### MEAN PARAMETERS
    
    # Units: 10 nm as length unit
    from_um_factor = 10e-3 # Conversion of 1 μm to my length unit (=10nm/1μm)
    
    # Au sphere
    r = r / ( from_um_factor * 1e3 ) # Now in Meep units
    displacement = displacement / ( from_um_factor * 1e3 ) # Now in Meep units
    medium = import_medium("Au", from_um_factor, paper=paper) # Medium of sphere: gold (Au)
    
    # Frequency and wavelength
    wlen_range = wlen_range / ( from_um_factor * 1e3 ) # Wavelength now in Meep units
    nfreq = 100 # Number of frequencies to discretize range
    cutoff = 3.2
    
    # Computation time
    enlapsed = []
    time_factor_cell = 1.2
    until_after_sources = False
    
    # Saving directories
    if series is None:
        series = f"TestParallelRes{resolution}"
    if folder is None:
        folder = "AuMieMediums/TestSubSurface"
    
    ### OTHER PARAMETERS
    
    # Units
    # uman = MeepUnitsManager(from_um_factor=from_um_factor)
    
    # Frequency and wavelength
    freq_range = 1/wlen_range # Hz range in Meep units from highest to lowest
    freq_center = np.mean(freq_range)
    freq_width = max(freq_range) - min(freq_range)
    
    # Space configuration
    pml_width = 0.38 * max(wlen_range)
    air_width = r/2 # 0.5 * max(wlen_range)
    
    #%% GENERAL GEOMETRY SETUP
    
    air_width = air_width - air_width%(1/resolution)
    
    pml_width = pml_width - pml_width%(1/resolution)
    pml_layers = [mp.PML(thickness=pml_width)]
       
    cell_width = 2 * (pml_width + air_width + r)
    cell_width = cell_width - cell_width%(1/resolution)
    cell_size = mp.Vector3(cell_width, cell_width, cell_width)
    
    source_center = -0.5*cell_width + pml_width
    print("Resto Source Center: {}".format(source_center%(1/resolution)))
    sources = [mp.Source(mp.GaussianSource(freq_center,
                                           fwidth=freq_width,
                                           is_integrated=True,
                                           cutoff=cutoff),
                         center=mp.Vector3(source_center),
                         size=mp.Vector3(0, cell_width, cell_width),
                         component=mp.Ez)]
    # Ez-polarized planewave pulse 
    # (its size parameter fills the entire cell in 2d)
    # >> The planewave source extends into the PML 
    # ==> is_integrated=True must be specified
    
    if time_factor_cell is not False:
        until_after_sources = time_factor_cell * cell_width
    else:
        if until_after_sources is False:
            raise ValueError("Either time_factor_cell or until_after_sources must be specified")
        time_factor_cell = until_after_sources/cell_width
    # Enough time for the pulse to pass through all the cell
    # Originally: Aprox 3 periods of lowest frequency, using T=λ/c=λ in Meep units 
    # Now: Aprox 3 periods of highest frequency, using T=λ/c=λ in Meep units 
       
    geometry = [mp.Block(material=mp.Medium(index=submerged_index),
                         center=mp.Vector3(-cell_width/2+(cell_width/2-r+displacement)/2+displacement,0,0),
                         size=mp.Vector3(cell_width/2+r-displacement, cell_width, cell_width)),
                mp.Block(material=mp.Medium(index=surface_index),
                         center=mp.Vector3(cell_width/2-(cell_width/2+r-displacement)/2+displacement,0,0),
                         size=mp.Vector3(cell_width/2-r+displacement, cell_width, cell_width)),
                mp.Sphere(material=medium,#mp.Medium(index=1.8),
                          center=mp.Vector3(),
                          radius=r)]
    # Au sphere with frequency-dependant characteristics imported from Meep.
    # Water sourrounding it
    # Glass underneath it
    
    home = vs.get_home()
    path = os.path.join(home, folder, f"{series}")
    if not os.path.isdir(path) and mp.am_master(): 
        vs.new_dir(path)
    file = lambda f : os.path.join(path, f)
    
    #%% FIRST RUN: SET UP
    
    sim = mp.Simulation(resolution=resolution,
                        cell_size=cell_size,
                        boundary_layers=pml_layers,
                        sources=sources,
                        k_point=mp.Vector3(),
                        geometry=[*geometry[0:1]])
    # >> k_point zero specifies boundary conditions needed
    # for the source to be infinitely extended
    
    # Scattered power --> Computed by surrounding it with closed DFT flux box 
    # (its size and orientation are irrelevant because of Poynting's theorem) 
    box_x1 = sim.add_flux(freq_center, freq_width, nfreq, 
                          mp.FluxRegion(center=mp.Vector3(x=-r),
                                        size=mp.Vector3(0,2*r,2*r)))
    box_x2 = sim.add_flux(freq_center, freq_width, nfreq, 
                          mp.FluxRegion(center=mp.Vector3(x=+r),
                                        size=mp.Vector3(0,2*r,2*r)))
    box_y1 = sim.add_flux(freq_center, freq_width, nfreq,
                          mp.FluxRegion(center=mp.Vector3(y=-r),
                                        size=mp.Vector3(2*r,0,2*r)))
    box_y2 = sim.add_flux(freq_center, freq_width, nfreq,
                          mp.FluxRegion(center=mp.Vector3(y=+r),
                                        size=mp.Vector3(2*r,0,2*r)))
    box_z1 = sim.add_flux(freq_center, freq_width, nfreq,
                          mp.FluxRegion(center=mp.Vector3(z=-r),
                                        size=mp.Vector3(2*r,2*r,0)))
    box_z2 = sim.add_flux(freq_center, freq_width, nfreq,
                          mp.FluxRegion(center=mp.Vector3(z=+r),
                                        size=mp.Vector3(2*r,2*r,0)))
    # Funny you can encase the sphere (r radius) so closely (2r-sided box)
    
    #%% FIRST RUN: INITIALIZE
    
    temp = time()
    sim.init_sim()
    enlapsed.append( time() - temp )
    
    #%% FIRST RUN: SIMULATION NEEDED TO NORMALIZE
    
    temp = time()
    sim.run(until_after_sources=until_after_sources)
        #     mp.stop_when_fields_decayed(
        # np.mean(wlen_range), # dT = mean period of source
        # mp.Ez, # Component of field to check
        # mp.Vector3(0.5*cell_width - pml_width, 0, 0), # Where to check
        # 1e-3)) # Factor to decay
    enlapsed.append( time() - temp )
    
    freqs = np.asarray(mp.get_flux_freqs(box_x1))
    box_x1_data = sim.get_flux_data(box_x1)
    box_x2_data = sim.get_flux_data(box_x2)
    box_y1_data = sim.get_flux_data(box_y1)
    box_y2_data = sim.get_flux_data(box_y2)
    box_z1_data = sim.get_flux_data(box_z1)
    box_z2_data = sim.get_flux_data(box_z2)
    
    box_x1_flux0 = np.asarray(mp.get_fluxes(box_x1))
    box_x2_flux0 = np.asarray(mp.get_fluxes(box_x2))
    box_y1_flux0 = np.asarray(mp.get_fluxes(box_y1))
    box_y2_flux0 = np.asarray(mp.get_fluxes(box_y2))
    box_z1_flux0 = np.asarray(mp.get_fluxes(box_z1))
    box_z2_flux0 = np.asarray(mp.get_fluxes(box_z2))
    
    sim.reset_meep()
    
    #%% SAVE MID DATA
    
    params = dict(
        from_um_factor=from_um_factor,
        resolution=resolution,
        r=r,
        displacement=displacement,
        paper=paper,
        submerged_index=submerged_index,
        surface_index=surface_index,
        wlen_range=wlen_range,
        nfreq=nfreq,
        cutoff=cutoff,
        pml_width=pml_width,
        air_width=air_width,
        source_center=source_center,
        enlapsed=enlapsed,
        series=series,
        folder=folder,
        home=home,
        until_after_sources=until_after_sources,
        time_factor_cell=time_factor_cell,
        second_time_factor=second_time_factor,
        )
    
    data_mid = np.array([1e3*from_um_factor/freqs, box_x1_flux0, box_x2_flux0, 
                         box_y1_flux0, box_y2_flux0, box_z1_flux0, box_z2_flux0]).T
    
    header_mid = ["Longitud de onda [nm]", 
                  "Flujo X10 [u.a.]",
                  "Flujo X20 [u.a]",
                  "Flujo Y10 [u.a]",
                  "Flujo Y20 [u.a]",
                  "Flujo Z10 [u.a]",
                  "Flujo Z20 [u.a]"]
    
    if mp.am_master():    
        vs.savetxt(file("MidFlux.txt"), data_mid, 
                   header=header_mid, footer=params)
    
    #%% PLOT FLUX FOURIER MID DATA
    
    if mp.my_rank()==1:
        ylims = (np.min(data_mid[:,1:]), np.max(data_mid[:,1:]))
        ylims = (ylims[0]-.1*(ylims[1]-ylims[0]),
                 ylims[1]+.1*(ylims[1]-ylims[0]))
        
        fig, ax = plt.subplots(3, 2, sharex=True)
        fig.subplots_adjust(hspace=0, wspace=.05)
        for a in ax[:,1]:
            a.yaxis.tick_right()
            a.yaxis.set_label_position("right")
        for a, h in zip(np.reshape(ax, 6), header_mid[1:]):
            a.set_ylabel(h)
        
        for d, a in zip(data_mid[:,1:].T, np.reshape(ax, 6)):
            a.plot(1e3*from_um_factor/freqs, d)
            a.set_ylim(*ylims)
        ax[-1,0].set_xlabel("Wavelength [nm]")
        ax[-1,1].set_xlabel("Wavelength [nm]")
        
        plt.savefig(file("MidFlux.png"))
    
    #%% SECOND RUN: SETUP
    
    sim = mp.Simulation(resolution=resolution,
                        cell_size=cell_size,
                        boundary_layers=pml_layers,
                        sources=sources,
                        k_point=mp.Vector3(),
                        geometry=geometry)
    
    box_x1 = sim.add_flux(freq_center, freq_width, nfreq, 
                          mp.FluxRegion(center=mp.Vector3(x=-r),
                                        size=mp.Vector3(0,2*r,2*r)))
    box_x2 = sim.add_flux(freq_center, freq_width, nfreq, 
                          mp.FluxRegion(center=mp.Vector3(x=+r),
                                        size=mp.Vector3(0,2*r,2*r)))
    box_y1 = sim.add_flux(freq_center, freq_width, nfreq, 
                          mp.FluxRegion(center=mp.Vector3(y=-r),
                                        size=mp.Vector3(2*r,0,2*r)))
    box_y2 = sim.add_flux(freq_center, freq_width, nfreq, 
                          mp.FluxRegion(center=mp.Vector3(y=+r),
                                        size=mp.Vector3(2*r,0,2*r)))
    box_z1 = sim.add_flux(freq_center, freq_width, nfreq, 
                          mp.FluxRegion(center=mp.Vector3(z=-r),
                                        size=mp.Vector3(2*r,2*r,0)))
    box_z2 = sim.add_flux(freq_center, freq_width, nfreq, 
                          mp.FluxRegion(center=mp.Vector3(z=+r),
                                        size=mp.Vector3(2*r,2*r,0)))
        
    #%% SECOND RUN: INITIALIZE
    
    temp = time()
    sim.init_sim()
    enlapsed.append( time() - temp )
    
    temp = time()
    sim.load_minus_flux_data(box_x1, box_x1_data)
    sim.load_minus_flux_data(box_x2, box_x2_data)
    sim.load_minus_flux_data(box_y1, box_y1_data)
    sim.load_minus_flux_data(box_y2, box_y2_data)
    sim.load_minus_flux_data(box_z1, box_z1_data)
    sim.load_minus_flux_data(box_z2, box_z2_data)
    enlapsed.append( time() - temp )
    del box_x1_data, box_x2_data, box_y1_data, box_y2_data
    del box_z1_data, box_z2_data
    
    #%% SECOND RUN: SIMULATION :D
    
    temp = time()
    sim.run(until_after_sources=second_time_factor*until_after_sources) 
        #     mp.stop_when_fields_decayed(
        # np.mean(wlen_range), # dT = mean period of source
        # mp.Ez, # Component of field to check
        # mp.Vector3(0.5*cell_width - pml_width, 0, 0), # Where to check
        # 1e-3)) # Factor to decay
    enlapsed.append( time() - temp )
    del temp
    # Aprox 30 periods of lowest frequency, using T=λ/c=λ in Meep units 
    
    box_x1_flux = np.asarray(mp.get_fluxes(box_x1))
    box_x2_flux = np.asarray(mp.get_fluxes(box_x2))
    box_y1_flux = np.asarray(mp.get_fluxes(box_y1))
    box_y2_flux = np.asarray(mp.get_fluxes(box_y2))
    box_z1_flux = np.asarray(mp.get_fluxes(box_z1))
    box_z2_flux = np.asarray(mp.get_fluxes(box_z2))
    
    #%% ANALYSIS
    
    scatt_flux = box_x1_flux - box_x2_flux
    scatt_flux = scatt_flux + box_y1_flux - box_y2_flux
    scatt_flux = scatt_flux + box_z1_flux - box_z2_flux
    
    intensity = box_x1_flux0/(2*r)**2
    # Flux of one of the six monitor planes / Área
    # (the closest one, facing the planewave source) 
    # This is why the six sides of the flux box are separated
    # (Otherwise, the box could've been one flux object with weights ±1 per side)
    
    scatt_cross_section = np.divide(scatt_flux, intensity)
    # Scattering cross section σ = 
    # = scattered power in all directions / incident intensity.
    
    scatt_eff_meep = -1 * scatt_cross_section / (np.pi*r**2)
    # Scattering efficiency =
    # = scattering cross section / cross sectional area of the sphere
    
    freqs = np.array(freqs)
    
    #%% SAVE FINAL DATA
    
    data = np.array([1e3*from_um_factor/freqs, scatt_eff_meep]).T
    
    header = ["Longitud de onda [nm]", 
              "Sección eficaz efectiva (Meep) [u.a.]"]
    
    data_base = np.array([1e3*from_um_factor/freqs, box_x1_flux0, box_x1_flux,
                          box_x2_flux, box_y1_flux, box_y2_flux, 
                          box_z1_flux, box_z2_flux, 
                          intensity, scatt_flux, scatt_cross_section]).T
    
    header_base = ["Longitud de onda [nm]", 
                    "Flujo X10 [u.a.]",
                    "Flujo X1 [u.a]",
                    "Flujo X2 [u.a]",
                    "Flujo Y1 [u.a]",
                    "Flujo Y2 [u.a]",
                    "Flujo Z1 [u.a]",
                    "Flujo Z2 [u.a]",
                    "Intensidad incidente [u.a.]", 
                    "Flujo scattereado [u.a.]",
                    "Sección eficaz de scattering [u.a.]"]
    
    if mp.am_master():
        vs.savetxt(file("Results.txt"), data, 
                   header=header, footer=params)
        vs.savetxt(file("BaseResults.txt"), data_base, 
                   header=header_base, footer=params)
    
    #%% PLOT SCATTERING
    
    if mp.my_rank()==1:
        plt.figure()
        plt.plot(1e3*from_um_factor/freqs, scatt_eff_meep,'bo-')
        plt.xlabel('Wavelength [nm]')
        plt.ylabel('Scattering efficiency [σ/πr$^{2}$]')
        plt.title('Mie Scattering of Au Sphere With {} nm Radius'.format(r*10))
        plt.tight_layout()
        plt.savefig(file("Scattering.png"))

    #%% PLOT FLUX FOURIER FINAL DATA
    
    if mp.am_master():
        ylims = (np.min(data_base[:,2:8]), np.max(data_base[:,2:8]))
        ylims = (ylims[0]-.1*(ylims[1]-ylims[0]),
                  ylims[1]+.1*(ylims[1]-ylims[0]))
        
        fig, ax = plt.subplots(3, 2, sharex=True)
        fig.subplots_adjust(hspace=0, wspace=.05)
        for a in ax[:,1]:
            a.yaxis.tick_right()
            a.yaxis.set_label_position("right")
        for a, h in zip(np.reshape(ax, 6), header_mid[1:]):
            a.set_ylabel(h)
        
        for d, a in zip(data_base[:,2:8].T, np.reshape(ax, 6)):
            a.plot(1e3*from_um_factor/freqs, d)
            a.set_ylim(*ylims)
        ax[-1,0].set_xlabel("Wavelength [nm]")
        ax[-1,1].set_xlabel("Wavelength [nm]")
        
        plt.savefig(file("FinalFlux.png"))
    
#%%

if __name__ == '__main__':
    main()
