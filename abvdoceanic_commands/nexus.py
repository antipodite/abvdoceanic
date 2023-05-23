"""
Write nexus file
"""
import csv

from pathlib import Path
from nexusmaker import load_cldf
from nexusmaker import NexusMaker
from nexusmaker import NexusMakerAscertained
from nexusmaker import NexusMakerAscertainedParameters
from nexusmaker.tools import remove_combining_cognates

from cldfcatalog import Config
from pyglottolog import Glottolog

root = Path(__file__).parent.parent


def register(parser):
    parser.add_argument(
        "--output",
        default="abvdoceanic.nex",
        help="output file name")
    parser.add_argument(
        "--ascertainment",
        default=None,
        choices=[None, 'overall', 'word'],
        help="set ascertainment mode")
    parser.add_argument(
        "--filter",
        default=None,
        type=Path,
        help="filename containing a list of parameters to remove")
    parser.add_argument(
        "--removecombined",
        default=None,
        type=int,
        help="set level at which to filter combined cognates")
    parser.add_argument(
        "--subtree",
        default=None,
        type=str,
        help="filter output to subtree below specified glottocode"
    )


def run(args):
    # Load glottolog clone
    cfg = Config.from_file()
    glottolog = Glottolog(cfg.get_clone("glottolog"))
    lgfile = root / 'cldf' / "languages.csv"
    mdfile = root / 'cldf' / "cldf-metadata.json"
    records = list(load_cldf(mdfile, table='FormTable'))
    args.log.info('%8d records loaded from %s' % (len(records), mdfile))
    
    # run filter if given
    if args.filter:
        for param in args.filter.read_text().split("\n"):
            nrecords = len(records)
            records = [
                r for r in records if r.Parameter.lower() != param.lower()
            ]
            change = nrecords - len(records)
            args.log.info('%8d records removed for parameter %s' % (
                change, param
            ))
            if change == 0:
                args.log.warn("No records removed for parameter %s" % param)

    if args.subtree:
        filtered = []
        subtree = glottolog.languoid(args.subtree)
        subgroup = [l.glottocode for l in subtree.iter_descendants()]
        # Resolve ABVD slug <-> glottocode mapping and filter languages not below gcode
        nrecords = len(records)
        with open(lgfile) as f:
            langs = [r for r in csv.DictReader(f, delimiter=",")]
        lookup = {row["ID"]: row["Glottocode"] for row in langs}
        # Do the filtering
        for r in records:
            gcode = lookup[r.Language_ID]
            if gcode in subgroup:
                filtered.append(r)
        records = filtered
        change = nrecords - len(records)
        args.log.info('%8d records pruned around subtree %s %s' % (
            change, args.subtree, subtree.name
        ))
        if change == 0:
            args.log.warn("No records removed for parameter %s" % subtree)

    args.log.info(
        '%8d records written to nexus %s using ascertainment=%s' % (
        len(records), args.output, args.ascertainment
    ))

    args.log.info(
        'writing nexus from %d records to %s using ascertainment=%s'
        % (len(records), args.output, args.ascertainment)
    )

    if args.ascertainment is None:
        nex = NexusMaker(
            data=records, remove_loans=True, unique_ids=True)
    elif args.ascertainment == 'overall':
        nex = NexusMakerAscertained(
            data=records, remove_loans=True, unique_ids=True)
    elif args.ascertainment == 'word':
        nex = NexusMakerAscertainedParameters(
            data=records, remove_loans=True, unique_ids=True)
    else:
        raise ValueError("Unknown Ascertainment %s" % args.ascertainment)

    if args.removecombined:
        nex = remove_combining_cognates(nex, keep=args.removecombined)
        args.log.info(
            'removing combined cognates with more than %d components' % args.removecombined
        )

    nex.write(filename=args.output)
