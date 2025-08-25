mkdir huggingface
cd huggingface
git lfs install

mkdir SaProt
cd SaProt
git clone https://huggingface.co/westlake-repl/SaProt_35M_AF2
git clone https://huggingface.co/westlake-repl/SaProt_650M_AF2
cd ..

mkdir SaProt_Adapter
cd SaProt_Adapter
git clone https://huggingface.co/SaProtHub/ACE2_Omicron_BQ.1.1_binding_affinity
git clone https://huggingface.co/SaProtHub/ACE2_Omicron_XBB.1.5_binding_affinity
git clone https://huggingface.co/SaProtHub/AVIDa-SARS-CoV-2-Alpha
git clone https://huggingface.co/SaProtHub/AVIDa-hIL6_Interaction_prediction
git clone https://huggingface.co/SaProtHub/DMS_AsCas12f
git clone https://huggingface.co/SaProtHub/DMS_BLAT_ECOLX
git clone https://huggingface.co/SaProtHub/DMS_DLG4_RAT
git clone https://huggingface.co/SaProtHub/DMS_GAL4_YEAST
git clone https://huggingface.co/SaProtHub/DMS_PTEN_HUMAN
git clone https://huggingface.co/SaProtHub/DMS_RASH_HUMAN
git clone https://huggingface.co/SaProtHub/DMS_UBC9_HUMAN
git clone https://huggingface.co/SaProtHub/DMS_YAP1_HUMAN
git clone https://huggingface.co/SaProtHub/GB1_fitness_prediction
git clone https://huggingface.co/SaProtHub/Mega-sacle-Protein-Stability-Prediction
git clone https://huggingface.co/SaProtHub/Model-AAV-650M
git clone https://huggingface.co/SaProtHub/Model-BetaLactamase-650M
git clone https://huggingface.co/SaProtHub/Model-Binary_Localization-650M
git clone https://huggingface.co/SaProtHub/Model-Binding_Site_Detection-650M
git clone https://huggingface.co/SaProtHub/Model-EYFP-650M
git clone https://huggingface.co/SaProtHub/Model-EYFP_100K-650M
git clone https://huggingface.co/SaProtHub/Model-Fluorescence-650M
git clone https://huggingface.co/SaProtHub/Model-Metal_Ion_Binding-650M
git clone https://huggingface.co/SaProtHub/Model-Stability-650M
git clone https://huggingface.co/SaProtHub/Model-Structural_Similarity-650M
git clone https://huggingface.co/SaProtHub/Model-Structure_Class-650M
git clone https://huggingface.co/SaProtHub/Model-Subcellular_Localization-650M
git clone https://huggingface.co/SaProtHub/Model-Thermostability-650M
git clone https://huggingface.co/SaProtHub/Omicron_BQ.1.1_Expr
git clone https://huggingface.co/SaProtHub/Omicron_XBB.1.5_Expr
git clone https://huggingface.co/SaProtHub/tm9d8s_fitness
cd ..
