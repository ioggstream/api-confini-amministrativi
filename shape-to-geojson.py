#!/usr/bin/env python
from glob import glob
from json import dumps
from os.path import basename, dirname
from pathlib import Path
from sys import exit
from zipfile import ZipFile

import click
import pytest
import requests

import shapefile

from pyproj import Transformer


@click.command()
@click.option("--shape", help="Source file", prompt="Enter the source file")
@click.option("--outfile", help="Destination file", prompt="Enter the destination file")
def main(shape, outfile):
    return convert(shape, outfile)


def write_file_to_path(fpath, text):
    Path(dirname(fpath)).mkdir(parents=True, exist_ok=True)
    return Path(fpath).write_text(text)


#
# Important: put the trasformer in a global variable!
#
transformer = Transformer.from_crs("epsg:32632", "epsg:4326")
transform_coordinates = transformer.transform


def transform_geometry(geometry):
    if geometry["type"].lower() == "polygon":
        geometry["coordinates"] = [
            [transform_coordinates(*p) for p in line]
            for line in geometry["coordinates"]
        ]
        return geometry
    if geometry["type"].lower() == "multipolygon":
        geometry["coordinates"] = [
            [[transform_coordinates(*p) for p in line] for line in polygon]
            for polygon in geometry["coordinates"]
        ]
        return geometry
    raise NotImplementedError(geometry["type"])


def convert(fpath):
    reader = shapefile.Reader(fpath)
    fields = reader.fields[1:]
    field_names = [field[0] for field in fields]
    yield from [
        {
            "type": "Feature",
            "geometry": transform_geometry(sr.shape.__geo_interface__),
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


if __name__ == "__main__":
    exit(main())


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
    shapes = glob(f"{basedir}/*/*{label}*shp")
    for sfile in shapes:
        for feature in convert(sfile):
            yield feature
            break


import yaml


def test_transform_coordinates():
    fpath = "comune/010001.geojson"
    feature = yaml.safe_load(Path(fpath).read_text())
    geometry = feature["geometry"]
    coordinates = geometry["coordinates"]
    if geometry["type"].lower() == "polygon":
        geometry["coordinates"] = [
            [transform_coordinates(*p) for p in line] for line in coordinates
        ]
    else:
        raise NotImplementedError
    assert geometry["coordinates"][0][0] == (44.44871511679767, 8.669959531865064)


@pytest.mark.parametrize("feature", generate_features(label="01012020"))
def test_shp(feature):
    feature = feature
    fpath = feature_to_path(feature, label="01012020")
    write_file_to_path(fpath, dumps(feature, indent=2))


@pytest.mark.parametrize(
    "feature",
    [
        (
            {
                "properties": {
                    "COD_RIP": 1,
                    "COD_REG": 1,
                    "COD_PROV": 1,
                    "COD_CM": 201,
                    "COD_UTS": 201,
                    "PRO_COM": 1077,
                    "PRO_COM_T": "001077",
                    "COMUNE": "Chiaverano",
                    "COMUNE_A": "",
                    "CC_UTS": 0,
                }
            },
            "comune/001077.geojson",
        ),
        (
            {
                "properties": {
                    "COD_RIP": 1,
                    "COD_REG": 1,
                    "COD_PROV": 1,
                    "COD_CM": 201,
                    "COD_UTS": 201,
                    "DEN_PROV": "-",
                    "DEN_CM": "Torino",
                    "DEN_UTS": "Torino",
                    "SIGLA": "TO",
                    "TIPO_UTS": "Citta metropolitana",
                }
            },
            "unita-territoriale-sovracomunale/201.geojson",
        ),
        (
            {"properties": {"COD_RIP": 1, "COD_REG": 1, "DEN_REG": "Piemonte",}},
            "regione/1.geojson",
        ),
        (
            {"properties": {"COD_RIP": 1, "DEN_RIP": "Nord-Ovest"}},
            "ripartizione/1.geojson",
        ),
    ],
)
def test_create_path(feature):
    feature, fpath = feature
    assert feature_to_path(feature) == fpath
