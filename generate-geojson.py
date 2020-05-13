#!/usr/bin/env python
import logging
from glob import glob
from json import dumps
from os.path import basename, dirname
from pathlib import Path
from sys import exit
from zipfile import ZipFile

import requests
import yaml

import shapefile

log = logging.basicConfig(level=logging.INFO)


def write_file_to_path(fpath, text):
    Path(dirname(fpath)).mkdir(parents=True, exist_ok=True)
    return Path(fpath).write_text(text)


def convert(fpath):
    reader = shapefile.Reader(fpath)
    fields = reader.fields[1:]
    field_names = [field[0] for field in fields]
    yield from [
        {
            "type": "Feature",
            "geometry": sr.shape.__geo_interface__,
            "properties": dict(zip(field_names, sr.record)),
        }
        for sr in reader.shapeRecords()
    ]


def write_collection(dpath, feature_collection):
    return write_file_to_path(
        dpath,
        dumps({"type": "FeatureCollection", "features": feature_collection}, indent=2)
        + "\n",
    )


def process_source(source, docsdir=""):
    filename = basename(source["url"])
    label = source["label"]
    destdir = source["directory"]
    dpath = Path(filename)
    if not dpath.is_file():
        #log.info("Uncompress zip file")
        ret = requests.get(source["url"])
        dpath.write_bytes(ret.content)

    tmpdir = "./tmp"
    ZipFile(dpath.absolute()).extractall(tmpdir)

    features = generate_features(tmpdir, label=label)
    for f in features:
        fpath = feature_to_path(f, label=f"{docsdir}/{destdir}")
        write_file_to_path(fpath, dumps(f, indent=2))


def main():
    sources_text = Path("sources.yaml").read_text()
    sources = yaml.safe_load(sources_text)
    for source in sources["sorgenti"]:
        process_source(source, docsdir="build/")


def feature_to_path(feature, label=""):
    label = label or "."
    properties = feature["properties"]
    if "PRO_COM_T" in properties:
        return "{label}/comune/{PRO_COM_T}.geojson".format(label=label, **properties)
    if "COD_CM" in properties:
        return "{label}/unita-territoriale-sovracomunale/{COD_UTS}.geojson".format(
            label=label, **properties
        )
    if "COD_PROV" in properties:
        return "{label}/provincia/{COD_PROV}.geojson".format(label=label, **properties)
    if "COD_REG" in properties:
        return "{label}/regione/{COD_REG}.geojson".format(label=label, **properties)
    if "COD_RIP" in properties:
        return "{label}/ripartizione/{COD_RIP}.geojson".format(
            label=label, **properties
        )

    raise NotImplementedError


def generate_features(basedir=".", label="01012020"):
    shape_files = f"{basedir}/*/*/*{label}*shp"
    shapes = glob(shape_files)
    # log.info("Expression %r matches file %r", shape_files, shapes)
    for sfile in shapes:
        for feature in convert(sfile):
            yield feature


if __name__ == "__main__":
    exit(main())
