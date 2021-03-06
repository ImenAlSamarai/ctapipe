"""
Create a plot of where the integration window lays on the trace for the pixel
with the highest charge, its neighbours, and the pixel with the lowest max
charge and its neighbours. Also shows a disgram of which pixels count as a
neighbour, the camera image for the max charge timeslice, the true pe camera
image, and a calibrated camera image
"""

import numpy as np
from matplotlib import pyplot as plt
from traitlets import Dict, List, Int, Bool, Enum
from ctapipe.calib.camera.dl0 import CameraDL0Reducer
from ctapipe.calib.camera.dl1 import CameraDL1Calibrator
from ctapipe.calib.camera.r1 import CameraR1CalibratorFactory
from ctapipe.core import Tool
from ctapipe.image.charge_extractors import ChargeExtractorFactory
from ctapipe.io.eventsourcefactory import EventSourceFactory
from ctapipe.io.eventseeker import EventSeeker
from ctapipe.visualization import CameraDisplay


def plot(event, telid, chan, extractor_name):
    # Extract required images
    dl0 = event.dl0.tel[telid].pe_samples[chan]

    t_pe = event.mc.tel[telid].photo_electron_image
    dl1 = event.dl1.tel[telid].image[chan]
    max_time = np.unravel_index(np.argmax(dl0), dl0.shape)[1]
    max_charges = np.max(dl0, axis=1)
    max_pix = int(np.argmax(max_charges))
    min_pix = int(np.argmin(max_charges))

    geom = event.inst.subarray.tel[telid].camera
    nei = geom.neighbors

    # Get Neighbours
    max_pixel_nei = nei[max_pix]
    min_pixel_nei = nei[min_pix]

    # Get Windows
    windows = event.dl1.tel[telid].extracted_samples[chan]
    length = np.sum(windows, axis=1)
    start = np.argmax(windows, axis=1)
    end = start + length - 1

    # Draw figures
    ax_max_nei = {}
    ax_min_nei = {}
    fig_waveforms = plt.figure(figsize=(18, 9))
    fig_waveforms.subplots_adjust(hspace=.5)
    fig_camera = plt.figure(figsize=(15, 12))

    ax_max_pix = fig_waveforms.add_subplot(4, 2, 1)
    ax_min_pix = fig_waveforms.add_subplot(4, 2, 2)
    ax_max_nei[0] = fig_waveforms.add_subplot(4, 2, 3)
    ax_min_nei[0] = fig_waveforms.add_subplot(4, 2, 4)
    ax_max_nei[1] = fig_waveforms.add_subplot(4, 2, 5)
    ax_min_nei[1] = fig_waveforms.add_subplot(4, 2, 6)
    ax_max_nei[2] = fig_waveforms.add_subplot(4, 2, 7)
    ax_min_nei[2] = fig_waveforms.add_subplot(4, 2, 8)

    ax_img_nei = fig_camera.add_subplot(2, 2, 1)
    ax_img_max = fig_camera.add_subplot(2, 2, 2)
    ax_img_true = fig_camera.add_subplot(2, 2, 3)
    ax_img_cal = fig_camera.add_subplot(2, 2, 4)

    # Draw max pixel traces
    ax_max_pix.plot(dl0[max_pix])
    ax_max_pix.set_xlabel("Time (ns)")
    ax_max_pix.set_ylabel("DL0 Samples (ADC)")
    ax_max_pix.set_title("(Max) Pixel: {}, True: {}, Measured = {:.3f}"
                         .format(max_pix, t_pe[max_pix], dl1[max_pix]))
    max_ylim = ax_max_pix.get_ylim()
    ax_max_pix.plot([start[max_pix], start[max_pix]],
                    ax_max_pix.get_ylim(), color='r', alpha=1)
    ax_max_pix.plot([end[max_pix], end[max_pix]],
                    ax_max_pix.get_ylim(), color='r', alpha=1)
    for i, ax in ax_max_nei.items():
        if len(max_pixel_nei) > i:
            pix = max_pixel_nei[i]
            ax.plot(dl0[pix])
            ax.set_xlabel("Time (ns)")
            ax.set_ylabel("DL0 Samples (ADC)")
            ax.set_title("(Max Nei) Pixel: {}, True: {}, Measured = {:.3f}"
                         .format(pix, t_pe[pix], dl1[pix]))
            ax.set_ylim(max_ylim)
            ax.plot([start[pix], start[pix]],
                    ax.get_ylim(), color='r', alpha=1)
            ax.plot([end[pix], end[pix]],
                    ax.get_ylim(), color='r', alpha=1)

    # Draw min pixel traces
    ax_min_pix.plot(dl0[min_pix])
    ax_min_pix.set_xlabel("Time (ns)")
    ax_min_pix.set_ylabel("DL0 Samples (ADC)")
    ax_min_pix.set_title("(Min) Pixel: {}, True: {}, Measured = {:.3f}"
                         .format(min_pix, t_pe[min_pix], dl1[min_pix]))
    ax_min_pix.set_ylim(max_ylim)
    ax_min_pix.plot([start[min_pix], start[min_pix]],
                    ax_min_pix.get_ylim(), color='r', alpha=1)
    ax_min_pix.plot([end[min_pix], end[min_pix]],
                    ax_min_pix.get_ylim(), color='r', alpha=1)
    for i, ax in ax_min_nei.items():
        if len(min_pixel_nei) > i:
            pix = min_pixel_nei[i]
            ax.plot(dl0[pix])
            ax.set_xlabel("Time (ns)")
            ax.set_ylabel("DL0 Samples (ADC)")
            ax.set_title("(Min Nei) Pixel: {}, True: {}, Measured = {:.3f}"
                         .format(pix, t_pe[pix], dl1[pix]))
            ax.set_ylim(max_ylim)
            ax.plot([start[pix], start[pix]],
                    ax.get_ylim(), color='r', alpha=1)
            ax.plot([end[pix], end[pix]],
                    ax.get_ylim(), color='r', alpha=1)

    # Draw cameras
    nei_camera = np.zeros_like(max_charges, dtype=np.int)
    nei_camera[min_pixel_nei] = 2
    nei_camera[min_pix] = 1
    nei_camera[max_pixel_nei] = 3
    nei_camera[max_pix] = 4
    camera = CameraDisplay(geom, ax=ax_img_nei)
    camera.image = nei_camera
    ax_img_nei.set_title("Neighbour Map")
    ax_img_nei.annotate("Pixel: {}".format(max_pix),
                        xy=(geom.pix_x.value[max_pix],
                            geom.pix_y.value[max_pix]),
                        xycoords='data', xytext=(0.05, 0.98),
                        textcoords='axes fraction',
                        arrowprops=dict(facecolor='red', width=2,
                                        alpha=0.4),
                        horizontalalignment='left',
                        verticalalignment='top')
    ax_img_nei.annotate("Pixel: {}".format(min_pix),
                        xy=(geom.pix_x.value[min_pix],
                            geom.pix_y.value[min_pix]),
                        xycoords='data', xytext=(0.05, 0.94),
                        textcoords='axes fraction',
                        arrowprops=dict(facecolor='orange', width=2,
                                        alpha=0.4),
                        horizontalalignment='left',
                        verticalalignment='top')
    camera = CameraDisplay(geom, ax=ax_img_max)
    camera.image = dl0[:, max_time]
    camera.add_colorbar(ax=ax_img_max, label="DL0 Samples (ADC)")
    ax_img_max.set_title("Max Timeslice (T = {})".format(max_time))
    ax_img_max.annotate("Pixel: {}".format(max_pix),
                        xy=(geom.pix_x.value[max_pix],
                            geom.pix_y.value[max_pix]),
                        xycoords='data', xytext=(0.05, 0.98),
                        textcoords='axes fraction',
                        arrowprops=dict(facecolor='red', width=2,
                                        alpha=0.4),
                        horizontalalignment='left',
                        verticalalignment='top')
    ax_img_max.annotate("Pixel: {}".format(min_pix),
                        xy=(geom.pix_x.value[min_pix],
                            geom.pix_y.value[min_pix]),
                        xycoords='data', xytext=(0.05, 0.94),
                        textcoords='axes fraction',
                        arrowprops=dict(facecolor='orange', width=2,
                                        alpha=0.4),
                        horizontalalignment='left',
                        verticalalignment='top')

    camera = CameraDisplay(geom, ax=ax_img_true)
    camera.image = t_pe
    camera.add_colorbar(ax=ax_img_true, label="True Charge (p.e.)")
    ax_img_true.set_title("True Charge")
    ax_img_true.annotate("Pixel: {}".format(max_pix),
                         xy=(geom.pix_x.value[max_pix],
                             geom.pix_y.value[max_pix]),
                         xycoords='data', xytext=(0.05, 0.98),
                         textcoords='axes fraction',
                         arrowprops=dict(facecolor='red', width=2,
                                         alpha=0.4),
                         horizontalalignment='left',
                         verticalalignment='top')
    ax_img_true.annotate("Pixel: {}".format(min_pix),
                         xy=(geom.pix_x.value[min_pix],
                             geom.pix_y.value[min_pix]),
                         xycoords='data', xytext=(0.05, 0.94),
                         textcoords='axes fraction',
                         arrowprops=dict(facecolor='orange', width=2,
                                         alpha=0.4),
                         horizontalalignment='left',
                         verticalalignment='top')

    camera = CameraDisplay(geom, ax=ax_img_cal)
    camera.image = dl1
    camera.add_colorbar(ax=ax_img_cal,
                        label="Calib Charge (Photo-electrons)")
    ax_img_cal.set_title("Charge (integrator={})".format(extractor_name))
    ax_img_cal.annotate("Pixel: {}".format(max_pix),
                        xy=(geom.pix_x.value[max_pix],
                            geom.pix_y.value[max_pix]),
                        xycoords='data', xytext=(0.05, 0.98),
                        textcoords='axes fraction',
                        arrowprops=dict(facecolor='red', width=2,
                                        alpha=0.4),
                        horizontalalignment='left',
                        verticalalignment='top')
    ax_img_cal.annotate("Pixel: {}".format(min_pix),
                        xy=(geom.pix_x.value[min_pix],
                            geom.pix_y.value[min_pix]),
                        xycoords='data', xytext=(0.05, 0.94),
                        textcoords='axes fraction',
                        arrowprops=dict(facecolor='orange', width=2,
                                        alpha=0.4),
                        horizontalalignment='left',
                        verticalalignment='top')

    fig_waveforms.suptitle("Integrator = {}".format(extractor_name))
    fig_camera.suptitle("Camera = {}".format(geom.cam_id))

    plt.show()


class DisplayIntegrator(Tool):
    name = "DisplayIntegrator"
    description = "Calibrate dl0 data to dl1, and plot the various camera " \
                  "images that characterise the event and calibration. Also " \
                  "plot some examples of waveforms with the " \
                  "integration window."

    event_index = Int(0, help='Event index to view.').tag(config=True)
    use_event_id = Bool(False, help='event_index will obtain an event using'
                                    'event_id instead of '
                                    'index.').tag(config=True)
    telescope = Int(None, allow_none=True,
                    help='Telescope to view. Set to None to display the first'
                         'telescope with data.').tag(config=True)
    channel = Enum([0, 1], 0, help='Channel to view').tag(config=True)

    aliases = Dict(dict(r='EventSourceFactory.product',
                        f='EventSourceFactory.input_url',
                        max_events='EventSourceFactory.max_events',
                        extractor='ChargeExtractorFactory.product',
                        window_width='ChargeExtractorFactory.window_width',
                        window_shift='ChargeExtractorFactory.window_shift',
                        sig_amp_cut_HG='ChargeExtractorFactory.sig_amp_cut_HG',
                        sig_amp_cut_LG='ChargeExtractorFactory.sig_amp_cut_LG',
                        lwt='ChargeExtractorFactory.lwt',
                        clip_amplitude='CameraDL1Calibrator.clip_amplitude',
                        radius='CameraDL1Calibrator.radius',
                        E='DisplayIntegrator.event_index',
                        T='DisplayIntegrator.telescope',
                        C='DisplayIntegrator.channel',
                        ))
    flags = Dict(dict(id=({'DisplayDL1Calib': {'use_event_index': True}},
                          'event_index will obtain an event using '
                          'event_id instead of index.')
                      ))
    classes = List([EventSourceFactory,
                    ChargeExtractorFactory,
                    CameraDL1Calibrator,
                    ])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.eventseeker = None
        self.r1 = None
        self.dl0 = None
        self.extractor = None
        self.dl1 = None

    def setup(self):
        self.log_format = "%(levelname)s: %(message)s [%(name)s.%(funcName)s]"
        kwargs = dict(config=self.config, tool=self)

        eventsource = EventSourceFactory.produce(**kwargs)
        self.eventseeker = EventSeeker(eventsource, **kwargs)

        self.extractor = ChargeExtractorFactory.produce(**kwargs)

        self.r1 = CameraR1CalibratorFactory.produce(
            eventsource=eventsource,
            **kwargs
        )

        self.dl0 = CameraDL0Reducer(**kwargs)

        self.dl1 = CameraDL1Calibrator(extractor=self.extractor, **kwargs)


    def start(self):
        event_num = self.event_index
        if self.use_event_id:
            event_num = str(event_num)
        event = self.eventseeker[event_num]

        # Calibrate
        self.r1.calibrate(event)
        self.dl0.reduce(event)
        self.dl1.calibrate(event)

        # Select telescope
        tels = list(event.r0.tels_with_data)
        telid = self.telescope
        if telid is None:
            telid = tels[0]
        if telid not in tels:
            self.log.error("[event] please specify one of the following "
                           "telescopes for this event: {}".format(tels))
            exit()

        extractor_name = self.extractor.__class__.__name__

        plot(event, telid, self.channel, extractor_name)

    def finish(self):
        pass


if __name__ == '__main__':
    exe = DisplayIntegrator()
    exe.run()
