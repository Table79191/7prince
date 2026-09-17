# Summary
UD_English-CTeTex is a technical text corpus annotated in Universal Dependency syntax containing 196 software requirements.

# Introduction

The original sentences of the corpus are taken mainly from the [PURE corpus](https://ieeexplore.ieee.org/document/8049173) of software requirement specifications (SRS), as well as other SRS documents available publicly on the web.


## Splitting
The whole corpus contains 9,273 tokens in 276 sentences for 196 software requirements. Many individual software requirements were selected from the same SRS document.

As it is below the threshold of 20k tokens, it was not split for train/dev/test.


The document id used in the files are related to the original file name in the PURE corpus suffixed with the document section, followed optionally with the requirement ID when the section lists multiple requirements.
For example "001_npac_6.4.3_R6-30.1" if taken from document 001_npac.pdf in the original corpus, and the requirement is in section 6.4.3. In this section, the requirement is identified as 6-30.1 in a table.

## Specificities

While it's not defined in the UD guidelines, we added a "LineAfter=Yes" feature in the MISC column to indicate when a line skip was found in the original text, in order to be able to recreate it. This is due to a particularity of some technical texts (and often in SRS documents) when a long sentence (often with an enumeration of items) is being split on multiple lines, with fragments still referring to the starting partial sentence.

Still, this does not make it possible to reproduce the original text in its entirety. For example, in document id 2001_npac_6.8_RR6-44, the sentence parts starting with a dash were represented as indented sub-lists of the main list items. Other requirements have a similar case (2000_nasax38_3.3.7, 2007_ertms_3.9.1.1, etc) with some variations.

## Acknowledgments
We would like to thank the Natural Sciences and Engineering Research Council of Canada for the grant on the IVVES project that made this dataset possible.

## References

**(Hassert & al. 2021)** Naïma Hassert, Pierre André Ménard, Edith Galy. (2021) [UD on Software Requirements: Application and Challenges](https://aclanthology.org/2021.udw-1.5/). Proc. of Fifth Workshop on Universal Dependencies, Sofia, Bulgaria.

```
@inproceedings{hassert-etal-2021-ud,
    title = "{UD} on Software Requirements: Application and Challenges",
    author = {Hassert, Na{\"\i}ma  and
      M{\'e}nard, Pierre Andr{\'e}  and
      Galy, Edith},
    editor = "de Lhoneux, Miryam  and
      Tsarfaty, Reut",
    booktitle = "Proceedings of the Fifth Workshop on Universal Dependencies (UDW, SyntaxFest 2021)",
    month = dec,
    year = "2021",
    address = "Sofia, Bulgaria",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2021.udw-1.5",
    pages = "62--74",
}
```


# Changelog

* 2025-08-09 v2.16
  * Added lemmas

* 2022-05-15 v2.10
  * Initial release in Universal Dependencies.


<pre>
=== Machine-readable metadata (DO NOT REMOVE!) ================================
Data available since: UD v2.14
License: CC BY-SA 4.0
Includes text: yes
Parallel: no
Genre: nonfiction
Lemmas: manual native
UPOS: manual native
XPOS: not available
Features: manual native
Relations: manual native
Contributors: Hassert, Naïma; Ménard, Pierre André; Galy, Edith
Contributing: here
Contact: pamenard@gmail.com
===============================================================================
</pre>
