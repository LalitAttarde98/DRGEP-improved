"""writes a solution object to a cantera cti file.

currently only works for Elementary, Falloff, Plog and ThreeBody Reactions
Cantera development version 2.3.0a2 required
"""

import os
import math
from textwrap import fill

import cantera as ct

# number of calories in 1000 Joules
CALORIES_CONSTANT = 4184.0

# Conversion from 1 debye to coulomb-meters
DEBEYE_CONVERSION = 3.33564e-30

indent = ['',
          ' ',
          '  ',
          '   ',
          '    ',
          '     ',
          '      ',
          '       ',
          '        ',
          '          ',
          '           ',
          '            ',
          '             ',
          '              ',
          '               ',
          '                '
          ]


def section_break(section_title):
    """Return string with break and new section title

    Parameters
    ----------
    section_title : str
        title string for next section break
    
    Returns
    -------
    str
        String with section title and breaks

    """
    return('#' + '-' * 75 + '\n' + 
           f'#  {section_title}\n' +
           '#' + '-' * 75 + '\n\n'
           )


def build_arrhenius(rate, reaction_order, reaction_type):
    """Builds Arrhenius coefficient string based on reaction type.

    Parameters
    ----------
    rate : cantera.Arrhenius
        Arrhenius-form reaction rate coefficient
    reaction_order : int or float
        Order of reaction (sum of reactant stoichiometric coefficients)
    reaction_type : {cantera.ElementaryReaction, cantera.ThreeBodyReaction, cantera.PlogReaction}
        Type of reaction

    Returns
    -------
    str
        String with Arrhenius coefficients

    """
    if reaction_type in [ct.ElementaryReaction, ct.PlogReaction]:
        pre_exponential_factor = rate.pre_exponential_factor * 1e3**(reaction_order - 1)

    elif reaction_type == ct.ThreeBodyReaction:
        pre_exponential_factor = rate.pre_exponential_factor * 1e3**reaction_order

    elif reaction_type in [ct.FalloffReaction, ct.ChemicallyActivatedReaction]:
        raise ValueError('Function does not support falloff or chemically activated reactions')
    else:
        raise NotImplementedError('Reaction type not supported: ', reaction_type)
    
    arrhenius = [f'{pre_exponential_factor:.6e}', 
                 str(rate.temperature_exponent), 
                 str(rate.activation_energy / CALORIES_CONSTANT)
                 ]
    return ', '.join(arrhenius)


def build_falloff_arrhenius(rate, reaction_order, reaction_type, pressure_limit):
    """Builds Arrhenius coefficient strings for falloff and chemically-activated reactions.

    Parameters
    ----------
    rate : cantera.Arrhenius
        Arrhenius-form reaction rate coefficient
    reaction_order : int or float
        Order of reaction (sum of reactant stoichiometric coefficients)
    reaction_type : {ct.FalloffReaction, ct.ChemicallyActivatedReaction}
        Type of reaction
    pressure_limit : {'high', 'low'}
        string designating pressure limit
    
    Returns
    -------
    str
        Arrhenius coefficient string

    """
    assert pressure_limit in ['low', 'high'], 'Pressure range needs to be high or low'

    # Each needs more complicated handling due if high- or low-pressure limit
    if reaction_type == ct.FalloffReaction:
        if pressure_limit == 'low':
            pre_exponential_factor = rate.pre_exponential_factor * 1e3**(reaction_order)
        elif pressure_limit == 'high':
            pre_exponential_factor = rate.pre_exponential_factor * 1e3**(reaction_order - 1)

    elif reaction_type == ct.ChemicallyActivatedReaction:
        if pressure_limit == 'low':
            pre_exponential_factor = rate.pre_exponential_factor * 1e3**(reaction_order - 1)
        elif pressure_limit == 'high':
            pre_exponential_factor = rate.pre_exponential_factor * 1e3**(reaction_order - 2)
    else:
        raise ValueError('Reaction type not supported: ', reaction_type)

    arrhenius = [f'{pre_exponential_factor:.6E}', 
                 str(rate.temperature_exponent), 
                 str(rate.activation_energy / CALORIES_CONSTANT)
                 ]
    return '[' + ', '.join(arrhenius) + ']'


def build_falloff(parameters, falloff_function):
    """Creates falloff reaction Troe parameter string

    Parameters
    ----------
    parameters : numpy.ndarray
        Array of falloff parameters; length varies based on ``falloff_function``
    falloff_function : {'Troe', 'SRI'}
        Type of falloff function

    Returns
    -------
    falloff_string : str
        String of falloff parameters

    """
    if falloff_function == 'Troe':
        falloff_string = ('Troe(' +
                          f'A = {parameters[0]}' +
                          f', T3 = {parameters[1]}' +
                          f', T1 = {parameters[2]}' +
                          f', T2 = {parameters[3]})'
                          )
    elif falloff_function == 'SRI':
        falloff_string = ('SRI(' + 
                          f'A = {parameters[0]}' +
                          f', B = {parameters[1]}' +
                          f', C = {parameters[2]}' +
                          f', D = {parameters[3]}' +
                          f', E = {parameters[4]})'
                          )
    else:
        raise NotImplementedError(f'Falloff function not supported: {falloff_function}')

    return falloff_string


def build_efficiencies(efficiencies, species_names, default_efficiency=1.0):
    """Creates line with list of third-body species efficiencies.

    Parameters
    ----------
    efficiencies : dict
        Dictionary of species efficiencies
    species_names : dict of str
        List of all species names
    default_efficiency : float, optional
        Default efficiency for all species; will be 0.0 for reactions with explicit third body

    Returns
    -------
    str
        Line with list of efficiencies

    """
    # Reactions with a default_efficiency of 0 and a single entry in the efficiencies dict
    # have an explicit third body specified.
    if len(efficiencies) == 1 and not default_efficiency:
        return ''

    reduced_efficiencies = {s:efficiencies[s] for s in efficiencies if s in species_names}
    return '  '.join([f'{s}:{v}' for s, v in reduced_efficiencies.items()])


def write(solution, output_filename='', path=''):
    import os
    if output_filename:
        output_filename = os.path.join(path, output_filename)
    else:
        output_filename = os.path.join(path, f'{solution.name}.yaml')
    
    if os.path.isfile(output_filename):
        os.remove(output_filename)

    solution.write_yaml(output_filename)
    return output_filename
