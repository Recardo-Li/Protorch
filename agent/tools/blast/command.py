import logging
import time
import os
import argparse
from io import BytesIO
import threading
from Bio.Blast import NCBIXML, qblast
from Bio.Blast.Applications import NcbiblastpCommandline  # Not directly used but shows context

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BlastRetriever():
    def __init__(self, blast_program='blastp', blast_database="nr", hitlist_size=50, expect_value=0.001):
        self.blast_program = blast_program
        self.blast_database = blast_database
        self.hitlist_size = int(hitlist_size)
        self.expect_value = float(expect_value)
        logger.info(f"Initializing BLAST retriever: program={blast_program}, database={blast_database}, hitlist_size={hitlist_size}, expect_value={expect_value}")
        return
    
    def search(self, sequence, save_path=None):
        """Perform BLAST search with detailed logging"""
        logger.info(f"Starting BLAST search, sequence length: {len(sequence)} characters")
        # Log the sequence only in debug mode to avoid cluttering the output
        logger.debug(f"Query sequence: {sequence[:50]}...{sequence[-50:]}" if len(sequence) > 100 else sequence)
        
        try:
            # Add clear warning about potential waiting time
            logger.warning("BLAST search in progress... This might take 1-2 minutes or longer depending on database size and network connection.")
            logger.info("Please be patient while we contact the NCBI servers...")
            
            start_time = time.time()
            
            # Perform BLAST search
            result_handle = qblast(
                program=self.blast_program, 
                database=self.blast_database, 
                hitlist_size=self.hitlist_size,
                expect=self.expect_value,
                sequence=sequence
            )
            
            elapsed = time.time() - start_time
            logger.info(f"BLAST search completed! Time taken: {elapsed:.2f} seconds")
            
            # Save results to file if save_path is provided
            if save_path:
                if os.path.dirname(save_path):
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                logger.info(f"Saving results to: {save_path}")
                with open(save_path, "wb") as out_handle:
                    out_handle.write(result_handle.read())
                # Reset the handle to beginning for parsing
                logger.info(f"Results saved to {save_path}")
            
        
        except Exception as e:
            logger.error(f"BLAST search failed: {str(e)}")
            raise

def main():
    logger.info("==== Starting BLAST analysis ====")
    start_time = time.time()
    
    # Initialize retriever with command line arguments
    retriever = BlastRetriever(
        blast_program=args.blast_program, 
        blast_database=args.blast_database if args.blast_database else "nr", 
        hitlist_size=args.hitlist_size if args.hitlist_size else 50,
        expect_value=args.expect_value if args.expect_value else 10
    )
    
    # Perform search
    try:
        retriever.search(sequence=args.query_sequence, save_path=args.save_path)

        
    except TimeoutError as e:
        logger.error(f"Operation timed out: {str(e)}")
        logger.error("Consider increasing the timeout value with --timeout")
    except Exception as e:
        logger.exception("An error occurred during processing")
    
    finally:
        elapsed = time.time() - start_time
        logger.info(f"==== Analysis completed! Total time: {elapsed:.2f} seconds ====")

def get_args():
    parser = argparse.ArgumentParser(description='Perform BLAST search and save results')
    parser.add_argument(
        '--query_sequence', type=str, required=True, 
        help='Protein sequence (as a string)'
    )
    parser.add_argument(
        '--blast_program', type=str, default='blastp', 
        choices=['blastp', 'blastn', 'blastx', 'tblastn'],
        help='BLAST program, default: blastp'
    )
    parser.add_argument(
        '--blast_database', type=str, default='nr', 
        help='Database to search against, default: nr'
    )
    parser.add_argument(
        '--hitlist_size', type=str, default='50', 
        help='Maximum number of hits to return, default: 50'
    )
    parser.add_argument(
        '--expect_value', type=str, default='10', 
        help='E-value threshold, default: 10'
    )
    parser.add_argument(
        '--save_path', type=str, required=True, 
        help='Path to save the results in XML format'
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='Enable debug mode (verbose logging)'
    )
    return parser.parse_args()

if __name__ == '__main__':
    args = get_args()
    
    # Set log level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    """
    Example command:
    python command.py \
        --query_sequence "VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSHGSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKLRVDPVNFKLLSHCLLVTLAAHLPAEFTPAVHASLDKFLASVSTVLTSKYR" \
        --blast_program "blastp" \
        --blast_database "nr" \
        --hitlist_size "50" \
        --expect_value "10" \
        --save_path "blast_results.xml" \
        --debug
    """
    main()