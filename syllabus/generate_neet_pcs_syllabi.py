# syllabus/generate_neet_pcs_syllabi.py
"""
DakshAI Generator Script: Populates structured AI Syllabus Trees for NEET and State PCS.
Ingests Exam -> Subject -> Topic -> Subtopic -> Concept hierarchy into Django ORM.
Can be safely re-run anytime.
"""

import os
import sys
import django

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nimides.settings")
    django.setup()

from django.db import transaction
from syllabus.models import Exam, Subject, Topic, Subtopic, Concept

# ---------------------------------------------------------
# SYLLABUS DATA DEFINITIONS
# ---------------------------------------------------------

NEET_SYLLABUS = {
    "exam": "NEET",
    "exam_type": "neet",
    "description": "National Eligibility cum Entrance Test for Medical (MBBS/BDS) Admissions",
    "subjects": [
        {
            "name": "Physics",
            "topics": [
                {
                    "name": "Mechanics & Motion",
                    "subtopics": [
                        {
                            "name": "Kinematics & Dynamics",
                            "concepts": [
                                {"name": "Motion in One & Two Dimensions", "description": "Kinematic equations, displacement vectors, and projectile trajectories."},
                                {"name": "Newton's Laws of Motion & Friction", "description": "Inertia, momentum conservation, static and kinetic friction."},
                                {"name": "Work Energy Theorem & Power", "description": "Work done by variable forces, potential energy curves, and power delivery."}
                            ]
                        },
                        {
                            "name": "Rotational Motion & Gravitation",
                            "concepts": [
                                {"name": "Center of Mass & Collisions", "description": "Elastic and inelastic collisions, momentum impulse, and center of mass motion."},
                                {"name": "Moment of Inertia & Torque", "description": "Parallel and perpendicular axis theorems, angular acceleration, and rolling motion."},
                                {"name": "Kepler's Laws & Gravitational Potential", "description": "Universal gravitation, orbital speed, escape velocity, and satellite motion."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Electrodynamics & Magnetism",
                    "subtopics": [
                        {
                            "name": "Electrostatics & Current Electricity",
                            "concepts": [
                                {"name": "Coulomb's Law & Electric Field", "description": "Electric charge interaction, field lines, electric dipole, and flux."},
                                {"name": "Gauss's Law & Capacitance", "description": "Gaussian surfaces, parallel plate capacitors, dielectric insertion, and energy storage."},
                                {"name": "Ohm's Law & Kirchhoff's Rules", "description": "Resistivity, temperature dependence, Wheatstone bridge, and complex circuit loops."}
                            ]
                        },
                        {
                            "name": "Magnetism & Electromagnetic Induction",
                            "concepts": [
                                {"name": "Biot-Savart Law & Ampere's Law", "description": "Magnetic field due to current loops, solenoids, and force on moving charges."},
                                {"name": "Electromagnetic Induction & AC Circuits", "description": "Faraday's law, Lenz's law, self/mutual inductance, LCR resonance, and transformers."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Thermal Physics & Waves",
                    "subtopics": [
                        {
                            "name": "Thermodynamics & Kinetic Theory",
                            "concepts": [
                                {"name": "Laws of Thermodynamics & Heat Engines", "description": "First law, isothermal/adiabatic processes, Carnot engine efficiency."},
                                {"name": "Kinetic Theory of Gases", "description": "Ideal gas equation, RMS speed, degrees of freedom, and equipartition of energy."}
                            ]
                        },
                        {
                            "name": "Oscillations & Waves",
                            "concepts": [
                                {"name": "Simple Harmonic Motion (SHM)", "description": "Displacement, velocity, acceleration, simple pendulum, and spring oscillations."},
                                {"name": "Wave Motion & Doppler Effect", "description": "Transverse & longitudinal waves, standing waves in organ pipes, beats, and Doppler shift."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Optics & Modern Physics",
                    "subtopics": [
                        {
                            "name": "Ray & Wave Optics",
                            "concepts": [
                                {"name": "Reflection & Refraction at Spherical Surfaces", "description": "Mirror formula, Snell's law, total internal reflection, lens maker's formula."},
                                {"name": "Young's Double Slit Interference & Diffraction", "description": "Coherent sources, fringe width calculation, single slit diffraction pattern."}
                            ]
                        },
                        {
                            "name": "Modern Physics & Semiconductors",
                            "concepts": [
                                {"name": "Photoelectric Effect & Matter Waves", "description": "Einstein's photoelectric equation, work function, and de Broglie wavelength."},
                                {"name": "Atomic Structure & Nuclear Reactions", "description": "Bohr's model, spectral series, mass defect, binding energy, and nuclear fission/fusion."},
                                {"name": "Semiconductor Diodes & Logic Gates", "description": "Intrinsic & extrinsic semiconductors, p-n junction diode characteristics, and truth tables."}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Chemistry",
            "topics": [
                {
                    "name": "Physical Chemistry",
                    "subtopics": [
                        {
                            "name": "Basic Principles & Atomic Structure",
                            "concepts": [
                                {"name": "Mole Concept & Concentration Terms", "description": "Stoichiometry, molarity, molality, mole fraction, and limiting reagent."},
                                {"name": "Quantum Numbers & Electronic Configuration", "description": "Bohr's radius, Heisenberg uncertainty, Aufbau principle, and Hund's rule."}
                            ]
                        },
                        {
                            "name": "Equilibrium & Electrochemistry",
                            "concepts": [
                                {"name": "Chemical & Ionic Equilibrium", "description": "Le Chatelier's principle, pH scale, buffer solutions, and solubility product (Ksp)."},
                                {"name": "Electrochemistry & Chemical Kinetics", "description": "Nernst equation, Kohlrausch law, rate laws, order of reaction, and Arrhenius equation."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Inorganic Chemistry",
                    "subtopics": [
                        {
                            "name": "Periodic Trends & Bonding",
                            "concepts": [
                                {"name": "Periodic Trends & Ionization Energy", "description": "Atomic radius, electronegativity, electron gain enthalpy, and metallic character."},
                                {"name": "Chemical Bonding & VSEPR Theory", "description": "Ionic vs covalent bonds, hybridization, dipole moment, and MO theory."}
                            ]
                        },
                        {
                            "name": "Coordination Compounds & Block Elements",
                            "concepts": [
                                {"name": "Coordination Chemistry & CFT", "description": "IUPAC nomenclature, isomerism, Werner's theory, and Crystal Field Splitting Energy."},
                                {"name": "p-Block & d-Block Elements", "description": "Group trends, inert pair effect, transition metal oxidation states, and colored complexes."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Organic Chemistry",
                    "subtopics": [
                        {
                            "name": "Hydrocarbons & Reaction Mechanisms",
                            "concepts": [
                                {"name": "General Organic Chemistry (GOC)", "description": "Inductive effect, resonance, hyperconjugation, electrophiles, and nucleophiles."},
                                {"name": "Alkanes, Alkenes & Alkynes", "description": "Markovnikov addition, ozonolysis, electrophilic addition, and acidity of alkynes."}
                            ]
                        },
                        {
                            "name": "Functional Groups & Biomolecules",
                            "concepts": [
                                {"name": "Alcohols, Phenols & Ethers", "description": "Preparation methods, acidity of phenol, Reimer-Tiemann reaction, and Williamson synthesis."},
                                {"name": "Aldehydes, Ketones & Carboxylic Acids", "description": "Nucleophilic addition, Aldol condensation, Cannizzaro reaction, and acidity trends."},
                                {"name": "Biomolecules & Polymers", "description": "Structure of glucose, amino acids, peptide bonds, DNA vs RNA, and essential polymers."}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Biology",
            "topics": [
                {
                    "name": "Botany & Plant Biology",
                    "subtopics": [
                        {
                            "name": "Plant Diversity & Structure",
                            "concepts": [
                                {"name": "Biological Classification & Kingdoms", "description": "Five kingdom classification, Monera, Protista, Fungi, and viral structures."},
                                {"name": "Plant Kingdom & Anatomy", "description": "Algae, Bryophytes, Pteridophytes, Gymnosperms, Angiosperms, and tissue systems."}
                            ]
                        },
                        {
                            "name": "Plant Physiology & Reproduction",
                            "concepts": [
                                {"name": "Photosynthesis & Respiration in Plants", "description": "Light reactions, Calvin cycle (C3/C4 pathways), Glycolysis, Krebs cycle, and ETS."},
                                {"name": "Sexual Reproduction in Flowering Plants", "description": "Microsporogenesis, megasporogenesis, double fertilization, and seed development."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Human Physiology & Zoology",
                    "subtopics": [
                        {
                            "name": "Human Systems I (Digestion, Respiration & Circulation)",
                            "concepts": [
                                {"name": "Digestion & Absorption", "description": "Alimentary canal, digestive enzymes, peristalsis, and nutrient absorption."},
                                {"name": "Breathing & Gas Exchange", "description": "Respiratory volumes (TV, IRV, ERV), oxygen-hemoglobin dissociation curve."},
                                {"name": "Body Fluids & Cardiac Cycle", "description": "Blood composition, double circulation, cardiac output, ECG interpretation."}
                            ]
                        },
                        {
                            "name": "Human Systems II (Excretion, Neural & Endocrine)",
                            "concepts": [
                                {"name": "Excretory System & Nephron Function", "description": "Ultrafiltration, reabsorption, counter-current mechanism, and micturition."},
                                {"name": "Neural Control & Synaptic Transmission", "description": "Action potential generation, nerve impulse conduction, reflex arc, and central nervous system."},
                                {"name": "Endocrine Glands & Hormones", "description": "Pituitary, thyroid, adrenal, pancreas hormones, and mechanism of hormone action."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Genetics, Evolution & Biotechnology",
                    "subtopics": [
                        {
                            "name": "Genetics & Molecular Basis",
                            "concepts": [
                                {"name": "Mendelian Genetics & Inheritance", "description": "Law of segregation, independent assortment, sex determination, and genetic disorders."},
                                {"name": "Molecular Basis of Inheritance", "description": "DNA double helix, semiconservative replication, transcription, translation, and lac operon."}
                            ]
                        },
                        {
                            "name": "Biotechnology & Ecology",
                            "concepts": [
                                {"name": "Recombinant DNA Technology & PCR", "description": "Restriction enzymes, gel electrophoresis, vectors, and PCR amplification cycles."},
                                {"name": "Ecology & Environmental Conservation", "description": "Population growth curves, food webs, ecological pyramids, and biodiversity hotspots."}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}

PCS_SYLLABUS = {
    "exam": "State PCS (BPSC, UPPCS, etc.)",
    "exam_type": "pcs",
    "description": "State Public Service Commission examinations (BPSC, UPPCS, MPPSC, RAS, etc.) General Studies",
    "subjects": [
        {
            "name": "Indian History & Culture",
            "topics": [
                {
                    "name": "Ancient & Medieval History",
                    "subtopics": [
                        {
                            "name": "Ancient Civilization & Empires",
                            "concepts": [
                                {"name": "Indus Valley Civilization & Town Planning", "description": "Harappan sites, trade networks, seals, urban drainage, and social structure."},
                                {"name": "Vedic Period, Buddhism & Jainism", "description": "Vedic literature, Varna system, doctrines of Buddha and Mahavira, and Sanghas."},
                                {"name": "Maurya & Gupta Golden Age", "description": "Ashoka's Dhamma edicts, Mauryan administration, Gupta art, science, and literature."}
                            ]
                        },
                        {
                            "name": "Medieval Empires & Culture",
                            "concepts": [
                                {"name": "Delhi Sultanate & Chola Administration", "description": "Iqta system, Market reforms of Alauddin Khalji, and Chola local self-governance."},
                                {"name": "Mughal Revenue System & Mansabdari", "description": "Zabt system, Akbar's religious policy, Mughal architecture, and regional powers."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Modern History & Freedom Struggle",
                    "subtopics": [
                        {
                            "name": "British Expansion & Revolt of 1857",
                            "concepts": [
                                {"name": "Land Revenue Systems & Colonial Impact", "description": "Permanent Settlement, Ryotwari, Mahalwari, and drain of wealth theory."},
                                {"name": "Revolt of 1857 & Early Uprisings", "description": "Causes, key leaders (Rani Laxmibai, Kunwar Singh), spread, and consequences."}
                            ]
                        },
                        {
                            "name": "Indian National Movement",
                            "concepts": [
                                {"name": "Formation of INC & Moderate vs Extremist Phase", "description": "Partition of Bengal, Swadeshi movement, Surat split, and Home Rule League."},
                                {"name": "Gandhian Era & Mass Movements", "description": "Non-Cooperation Movement, Civil Disobedience, Dandi March, and Quit India Movement."},
                                {"name": "Constitutional Developments & Independence", "description": "Government of India Acts (1919, 1935), Cabinet Mission, and Partition of 1947."}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Indian Polity & Governance",
            "topics": [
                {
                    "name": "Constitutional Framework",
                    "subtopics": [
                        {
                            "name": "Framing & Core Provisions",
                            "concepts": [
                                {"name": "Making of Indian Constitution & Preamble", "description": "Constituent assembly debates, source of provisions, and preamble philosophy."},
                                {"name": "Fundamental Rights, DPSP & Fundamental Duties", "description": "Articles 14-32, Directive Principles enforcement, and 86th Constitutional Amendment."}
                            ]
                        },
                        {
                            "name": "Union & State Executive & Legislature",
                            "concepts": [
                                {"name": "President, Prime Minister & Governor", "description": "Executive powers, ordinance making, pardoning powers, and constitutional position."},
                                {"name": "Parliamentary Procedure & Legislative Process", "description": "Money bills vs Ordinary bills, parliamentary committees, and joint sittings."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Judiciary & Local Self-Government",
                    "subtopics": [
                        {
                            "name": "Judicial System & Commissions",
                            "concepts": [
                                {"name": "Supreme Court, High Courts & Judicial Review", "description": "Writ jurisdiction, PIL, basic structure doctrine, and collegium system."},
                                {"name": "Constitutional & Statutory Bodies", "description": "Election Commission, UPSC, CAG, Finance Commission, and NITI Aayog."}
                            ]
                        },
                        {
                            "name": "Panchayati Raj & Local Governance",
                            "concepts": [
                                {"name": "73rd & 74th Constitutional Amendment Acts", "description": "Three-tier Panchayati Raj, Gram Sabha powers, Urban local bodies, and State Election Commission."}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Geography (India & World)",
            "topics": [
                {
                    "name": "Physical & World Geography",
                    "subtopics": [
                        {
                            "name": "Geomorphology & Climatology",
                            "concepts": [
                                {"name": "Plate Tectonics & Volcanism", "description": "Earth's interior structure, continental drift, earthquake waves, and faulting."},
                                {"name": "Atmospheric Pressure & Cyclones", "description": "Pressure belts, planetary winds, tropical vs temperate cyclones, and jet streams."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Geography of India",
                    "subtopics": [
                        {
                            "name": "Relief, Drainage & Climate",
                            "concepts": [
                                {"name": "Physiographic Divisions of India", "description": "Himalayan ranges, Indo-Gangetic plains, Peninsular plateau, and coastal plains."},
                                {"name": "River Systems & Indian Monsoon Mechanism", "description": "Himalayan vs Peninsular drainage, SW monsoon onset, El-Nino and IOD impact."}
                            ]
                        },
                        {
                            "name": "Resources & Agriculture",
                            "concepts": [
                                {"name": "Soils, Vegetation & Natural Resources", "description": "Alluvial, Black, Red soils, tropical rainforests, and major mineral distribution belts."},
                                {"name": "Cropping Patterns & Irrigation", "description": "Kharif, Rabi, Zaid crops, Green revolution, and major multi-purpose river projects."}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Indian Economy & Social Development",
            "topics": [
                {
                    "name": "Macroeconomics & Banking",
                    "subtopics": [
                        {
                            "name": "National Income & Fiscal Policy",
                            "concepts": [
                                {"name": "National Income Accounting & GDP", "description": "GDP, NDP, GNP, NNP, Real vs Nominal GDP, and Gross Value Added (GVA)."},
                                {"name": "Union Budget & Taxation", "description": "Revenue vs Capital expenditure, fiscal deficit types, GST structure, and FRBM Act."}
                            ]
                        },
                        {
                            "name": "Monetary Policy & Inflation",
                            "concepts": [
                                {"name": "RBI & Monetary Policy Tools", "description": "Repo rate, Reverse Repo, CRR, SLR, Open Market Operations, and Inflation targeting."},
                                {"name": "Poverty Alleviation & Unemployment Schemes", "description": "Poverty line committees (Tendulkar, Rangarajan), MGNREGA, and inclusive growth."}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "General Science & Environment",
            "topics": [
                {
                    "name": "General Science",
                    "subtopics": [
                        {
                            "name": "Everyday Physics & Chemistry",
                            "concepts": [
                                {"name": "Optics, Sound & Electromagnetism in Daily Life", "description": "Reflection, refraction, total internal reflection, Doppler effect, and household wiring."},
                                {"name": "Acids, Bases & Daily Chemicals", "description": "pH in daily life, soaps, detergents, polymers, fertilizers, and common salts."}
                            ]
                        },
                        {
                            "name": "Life Sciences & Human Health",
                            "concepts": [
                                {"name": "Human Physiology & Disease Control", "description": "Circulatory & digestive systems, viral/bacterial/protozoan diseases, and vaccines."},
                                {"name": "Vitamins, Minerals & Deficiency Diseases", "description": "Water-soluble vs Fat-soluble vitamins, deficiency syndromes, and balanced diet."}
                            ]
                        }
                    ]
                },
                {
                    "name": "Environment & Ecology",
                    "subtopics": [
                        {
                            "name": "Ecosystems & Biodiversity Conservation",
                            "concepts": [
                                {"name": "Ecosystem Dynamics & Food Chains", "description": "Trophic levels, bioaccumulation, biomagnification, and ecological pyramids."},
                                {"name": "Biodiversity Conservation & International Conventions", "description": "National parks, wildlife sanctuaries, RAMSAR sites, COP, and Paris Climate Agreement."}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}


@transaction.atomic
def ingest_syllabus(syllabus_data):
    exam_name = syllabus_data["exam"]
    exam_type = syllabus_data["exam_type"]
    desc = syllabus_data["description"]

    exam, created = Exam.objects.get_or_create(
        name=exam_name,
        defaults={
            "exam_type": exam_type,
            "description": desc
        }
    )
    if not created and exam.exam_type != exam_type:
        exam.exam_type = exam_type
        exam.save()

    total_subj = 0
    total_top = 0
    total_subtop = 0
    total_conc = 0

    for s_idx, subj_data in enumerate(syllabus_data["subjects"]):
        subject, _ = Subject.objects.get_or_create(
            exam=exam,
            name=subj_data["name"],
            defaults={"order": s_idx}
        )
        total_subj += 1

        for t_idx, top_data in enumerate(subj_data.get("topics", [])):
            topic, _ = Topic.objects.get_or_create(
                subject=subject,
                name=top_data["name"],
                defaults={"order": t_idx}
            )
            total_top += 1

            for st_idx, subtop_data in enumerate(top_data.get("subtopics", [])):
                subtopic, _ = Subtopic.objects.get_or_create(
                    topic=topic,
                    name=subtop_data["name"],
                    defaults={"order": st_idx}
                )
                total_subtop += 1

                for c_idx, conc_data in enumerate(subtop_data.get("concepts", [])):
                    Concept.objects.get_or_create(
                        subtopic=subtopic,
                        name=conc_data["name"],
                        defaults={
                            "description": conc_data.get("description", ""),
                            "order": c_idx,
                            "ai_meta": {}
                        }
                    )
                    total_conc += 1

    print(f"[SUCCESS] Loaded {exam_name} ({exam_type}): {total_subj} Subjects, {total_top} Topics, {total_subtop} Subtopics, {total_conc} Concepts!")


def main():
    print("[INGESTING] Ingesting NEET & State PCS Syllabi into DakshAI Database...")
    ingest_syllabus(NEET_SYLLABUS)
    ingest_syllabus(PCS_SYLLABUS)
    print("[DONE] All syllabi successfully generated and ingested!")

if __name__ == "__main__":
    main()
